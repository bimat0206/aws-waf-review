// --- START OF FILE logging/logging.go ---

package logging

import (
    "fmt"
    "io"
    "log"
    "os"
    "path/filepath"
    "time"
)

type Logger interface {
    Debugf(format string, v ...interface{})
    Infof(format string, v ...interface{})
    Warningf(format string, v ...interface{})
    Errorf(format string, v ...interface{})
    Fatalf(format string, v ...interface{})
    Debug(v ...interface{})
    Info(v ...interface{})
    Warning(v ...interface{})
    Error(v ...interface{})
    Fatal(v ...interface{})
    Close() error
}

// Rename defaultLogger to DefaultLogger so that it is exported.
type DefaultLogger struct {
    logger     *log.Logger
    level      string
    file       *os.File
    logPath    string
    multiWrite io.Writer
}

// SetupLogger creates a new logger that writes to both file and stdout.
func SetupLogger(logLevel string) (Logger, error) {
    // Create logs directory structure
    logDir := filepath.Join("logs", "app", time.Now().Format("2006-01-02"))
    if err := os.MkdirAll(logDir, 0755); err != nil {
        return nil, fmt.Errorf("failed to create log directory: %w", err)
    }

    // Create log file with timestamp
    logFileName := fmt.Sprintf("waf-retriever_%s.log", time.Now().Format("20060102_150405"))
    logPath := filepath.Join(logDir, logFileName)
    
    file, err := os.Create(logPath)
    if err != nil {
        return nil, fmt.Errorf("failed to create log file: %w", err)
    }

    multiWrite := io.MultiWriter(os.Stdout, file)
    logger := log.New(multiWrite, "[WAF-LOG-RETRIEVER] ", log.Ldate|log.Ltime|log.Lshortfile)

    return &DefaultLogger{
        logger:     logger,
        level:      logLevel,
        file:       file,
        logPath:    logPath,
        multiWrite: multiWrite,
    }, nil
}

func (l *DefaultLogger) Close() error {
    if l.file != nil {
        if err := l.file.Close(); err != nil {
            return fmt.Errorf("failed to close log file: %w", err)
        }
    }
    return nil
}

// Log level implementation functions
func (l *DefaultLogger) Debugf(format string, v ...interface{}) {
    if l.level == "DEBUG" {
        l.logger.Printf("[DEBUG] "+format, v...)
    }
}

func (l *DefaultLogger) Infof(format string, v ...interface{}) {
    if l.level == "DEBUG" || l.level == "INFO" {
        l.logger.Printf("[INFO] "+format, v...)
    }
}

func (l *DefaultLogger) Warningf(format string, v ...interface{}) {
    if l.level == "DEBUG" || l.level == "INFO" || l.level == "WARNING" {
        l.logger.Printf("[WARNING] "+format, v...)
    }
}

func (l *DefaultLogger) Errorf(format string, v ...interface{}) {
    l.logger.Printf("[ERROR] "+format, v...)
}

func (l *DefaultLogger) Fatalf(format string, v ...interface{}) {
    l.logger.Printf("[FATAL] "+format, v...)
    os.Exit(1)
}

// Non-formatted logging functions
func (l *DefaultLogger) Debug(v ...interface{}) {
    if l.level == "DEBUG" {
        l.logger.Println(append([]interface{}{"[DEBUG]"}, v...)...)
    }
}

func (l *DefaultLogger) Info(v ...interface{}) {
    if l.level == "DEBUG" || l.level == "INFO" {
        l.logger.Println(append([]interface{}{"[INFO]"}, v...)...)
    }
}

func (l *DefaultLogger) Warning(v ...interface{}) {
    if l.level == "DEBUG" || l.level == "INFO" || l.level == "WARNING" {
        l.logger.Println(append([]interface{}{"[WARNING]"}, v...)...)
    }
}

func (l *DefaultLogger) Error(v ...interface{}) {
    l.logger.Println(append([]interface{}{"[ERROR]"}, v...)...)
}

func (l *DefaultLogger) Fatal(v ...interface{}) {
    l.logger.Println(append([]interface{}{"[FATAL]"}, v...)...)
    os.Exit(1)
}

// --- END OF FILE logging/logging.go ---
