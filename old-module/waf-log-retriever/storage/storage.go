// Package storage provides functionality for managing WAF log files and directories
package storage

import (
	"compress/gzip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"
)

// StorageConfig holds configuration for the storage package
type StorageConfig struct {
	BaseDirectory      string
	RetentionDays      int
	CompressionEnabled bool
	CompressionLevel   int
}

// StorageManager handles file operations for WAF logs
type StorageManager struct {
	config StorageConfig
}

// NewStorageManager creates a new storage manager instance.
// If config.BaseDirectory is empty, it defaults to "../logs/raw" (one level above the code base).
func NewStorageManager(config StorageConfig) (*StorageManager, error) {
	if config.BaseDirectory == "" {
		config.BaseDirectory = "../logs/raw"
	}

	// Ensure compression level is valid
	if config.CompressionEnabled {
		if config.CompressionLevel < gzip.NoCompression || config.CompressionLevel > gzip.BestCompression {
			return nil, fmt.Errorf("invalid compression level: %d (must be between %d and %d)",
				config.CompressionLevel, gzip.NoCompression, gzip.BestCompression)
		}
	}

	sm := &StorageManager{config: config}

	// Ensure the base directory exists (this creates ../logs/raw if it doesn't exist)
	if err := sm.EnsureDirExists(sm.config.BaseDirectory); err != nil {
		return nil, fmt.Errorf("failed to create base directory: %w", err)
	}

	return sm, nil
}

// EnsureDirExists creates a directory if it doesn't exist and ensures it's writable
func (sm *StorageManager) EnsureDirExists(dirPath string) error {
	// Convert to absolute path for better error checking and logging
	absPath, err := filepath.Abs(dirPath)
	if err != nil {
		return fmt.Errorf("failed to resolve absolute path: %w", err)
	}

	// Basic security check - don't allow creating directories at root level
	if filepath.Dir(absPath) == "/" {
		return fmt.Errorf("refusing to create directory directly under root: %s", dirPath)
	}

	// Create all necessary parent directories
	if err := os.MkdirAll(absPath, 0755); err != nil {
		return fmt.Errorf("failed to create directory %s: %w", absPath, err)
	}

	// Verify the directory is writable by creating a test file
	testFile := filepath.Join(absPath, ".write_test")
	f, err := os.Create(testFile)
	if err != nil {
		return fmt.Errorf("directory %s exists but is not writable: %w", absPath, err)
	}
	f.Close()
	os.Remove(testFile)

	return nil
}

// GetLogFilePath generates the appropriate path for a WAF log file.
func (sm *StorageManager) GetLogFilePath(profileName, wafName string, timestamp time.Time) string {
	// Create directory structure: BaseDirectory/profile/waf/YYYY-MM-DD/HH/
	datePath := timestamp.Format("2006-01-02")
	hourPath := timestamp.Format("15")

	fileName := fmt.Sprintf("waf_log_%s.json", timestamp.Format("20060102_150405"))
	if sm.config.CompressionEnabled {
		fileName += ".gz"
	}

	return filepath.Join(
		sm.config.BaseDirectory,
		profileName,
		wafName,
		datePath,
		hourPath,
		fileName,
	)
}

// WriteLogFile writes log content to a file, with optional compression.
func (sm *StorageManager) WriteLogFile(logPath string, content []byte) error {
	// Ensure the directory exists
	if err := sm.EnsureDirExists(filepath.Dir(logPath)); err != nil {
		return fmt.Errorf("failed to create log directory: %w", err)
	}

	// Create the file
	file, err := os.Create(logPath)
	if err != nil {
		return fmt.Errorf("failed to create log file: %w", err)
	}
	defer file.Close()

	var writer io.Writer = file

	// If compression is enabled, wrap the file writer in a gzip writer
	if sm.config.CompressionEnabled {
		gw, err := gzip.NewWriterLevel(file, sm.config.CompressionLevel)
		if err != nil {
			return fmt.Errorf("failed to create gzip writer: %w", err)
		}
		defer gw.Close()
		writer = gw
	}

	// Write the content
	if _, err := writer.Write(content); err != nil {
		return fmt.Errorf("failed to write log content: %w", err)
	}

	return nil
}

// CleanupOldLogs removes log files older than the retention period.
func (sm *StorageManager) CleanupOldLogs() error {
	if sm.config.RetentionDays <= 0 {
		return nil // Retention disabled
	}

	cutoffTime := time.Now().AddDate(0, 0, -sm.config.RetentionDays)

	return filepath.Walk(sm.config.BaseDirectory, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err // Skip files that can't be accessed
		}

		// Skip directories
		if info.IsDir() {
			return nil
		}

		// Remove files older than retention period
		if info.ModTime().Before(cutoffTime) {
			if err := os.Remove(path); err != nil {
				return fmt.Errorf("failed to remove old log file %s: %w", path, err)
			}
		}

		return nil
	})
}

// IsCompressed checks if a file is gzip compressed.
func (sm *StorageManager) IsCompressed(filename string) bool {
	return filepath.Ext(filename) == ".gz"
}

// ReadLogFile reads a log file, assuming .gz files are compressed.
func (sm *StorageManager) ReadLogFile(filePath string) ([]byte, error) {
    file, err := os.Open(filePath)
    if err != nil {
        return nil, fmt.Errorf("failed to open log file: %w", err)
    }
    defer file.Close()

    // If the file has a .gz extension, assume it’s compressed and decompress it for reading
    if sm.IsCompressed(filePath) {
        gr, err := gzip.NewReader(file)
        if err != nil {
            return nil, fmt.Errorf("file %s has a .gz extension but is not a valid gzip file: %w", filePath, err)
        }
        defer gr.Close()
        // Read the decompressed content (for reading purposes only, not storage)
        content, err := io.ReadAll(gr)
        if err != nil {
            return nil, fmt.Errorf("failed to read decompressed log content: %w", err)
        }
        return content, nil
    }

    // For non-.gz files (unlikely in this context), read directly
    content, err := io.ReadAll(file)
    if err != nil {
        return nil, fmt.Errorf("failed to read log content: %w", err)
    }
    return content, nil
}

// ListLogFiles returns a list of log files in the storage directory.
func (sm *StorageManager) ListLogFiles(profileName, wafName string) ([]string, error) {
	searchPath := filepath.Join(sm.config.BaseDirectory, profileName, wafName)

	var files []string
	err := filepath.Walk(searchPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if !info.IsDir() && (filepath.Ext(path) == ".json" || filepath.Ext(path) == ".gz") {
			files = append(files, path)
		}

		return nil
	})

	if err != nil {
		return nil, fmt.Errorf("failed to list log files: %w", err)
	}

	return files, nil
}