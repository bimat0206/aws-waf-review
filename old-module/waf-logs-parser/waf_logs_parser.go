package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
)

// CloudWatchLogEntry represents the outer structure of each log entry
type CloudWatchLogEntry struct {
	Message   string `json:"@message"`
	Ptr       string `json:"@ptr"`
	Timestamp string `json:"@timestamp"`
}

// min returns the smaller of two integers
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func main() {
	// Define command line flags
	inputFile := flag.String("input", "", "Input file path (required)")
	outputFile := flag.String("output", "", "Output file path (defaults to stdout)")
	prettyPrint := flag.Bool("pretty", false, "Pretty-print JSON output")
	debugMode := flag.Bool("debug", false, "Enable debug output")
	validateJSON := flag.Bool("validate", true, "Validate inner JSON before processing (disable with -validate=false)")
	flag.Parse()

	// Validate required flags
	if *inputFile == "" {
		fmt.Fprintln(os.Stderr, "Error: input file is required")
		flag.Usage()
		os.Exit(1)
	}

	// Open input file
	file, err := os.Open(*inputFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error opening input file: %v\n", err)
		os.Exit(1)
	}
	defer file.Close()

	// Prepare output writer
	var output *os.File
	if *outputFile == "" {
		output = os.Stdout
	} else {
		output, err = os.Create(*outputFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error creating output file: %v\n", err)
			os.Exit(1)
		}
		defer output.Close()
	}

	// Read entire file content
	fileBytes, err := io.ReadAll(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		os.Exit(1)
	}

	// Track record counts
	processedRecords := 0
	validRecords := 0
	invalidRecords := 0
	skippedRecords := 0

	// Preprocess the file content to ensure proper JSON formatting
	fileContent := string(fileBytes)
	
	if *debugMode {
		fmt.Fprintf(os.Stderr, "File size: %d bytes\n", len(fileContent))
	}
	
	// Split the file by JSON objects - this looks for standalone JSON objects 
	// that each start with '{' and end with '}'
	objectStarts := []int{}
	objectEnds := []int{}
	braceLevel := 0
	inString := false
	escapeNext := false
	
	for i, c := range fileContent {
		if escapeNext {
			escapeNext = false
			continue
		}
		
		if c == '\\' && inString {
			escapeNext = true
			continue
		}
		
		if c == '"' && !escapeNext {
			inString = !inString
			continue
		}
		
		if !inString {
			if c == '{' {
				if braceLevel == 0 {
					objectStarts = append(objectStarts, i)
				}
				braceLevel++
			} else if c == '}' {
				braceLevel--
				if braceLevel == 0 {
					objectEnds = append(objectEnds, i)
				}
			}
		}
	}
	
	if *debugMode {
		fmt.Fprintf(os.Stderr, "Found %d potential JSON objects\n", len(objectStarts))
	}
	
	// Now extract and process each object
	for i := 0; i < len(objectStarts) && i < len(objectEnds); i++ {
		start := objectStarts[i]
		end := objectEnds[i]
		
		if end <= start {
			if *debugMode {
				fmt.Fprintf(os.Stderr, "Skipping invalid object range: start=%d, end=%d\n", start, end)
			}
			skippedRecords++
			continue
		}
		
		jsonObject := fileContent[start:end+1]
		jsonObject = strings.TrimSpace(jsonObject)
		
		// Skip if not a valid JSON object
		if !strings.HasPrefix(jsonObject, "{") || !strings.HasSuffix(jsonObject, "}") {
			if *debugMode {
				fmt.Fprintf(os.Stderr, "Skipping non-JSON object: %s\n", jsonObject[:min(50, len(jsonObject))])
			}
			skippedRecords++
			continue
		}
		
		// Parse the CloudWatch log entry
		var logEntry CloudWatchLogEntry
		decoder := json.NewDecoder(bytes.NewReader([]byte(jsonObject)))
		if err := decoder.Decode(&logEntry); err != nil {
			if *debugMode {
				fmt.Fprintf(os.Stderr, "Error parsing log entry: %v\n", err)
				fmt.Fprintf(os.Stderr, "JSON object: %s\n", jsonObject[:min(100, len(jsonObject))])
			}
			invalidRecords++
			continue
		}
		
		processedRecords++
		
		// Extract and output the inner message content
		if logEntry.Message != "" {
			// Optionally validate the inner JSON
			if *validateJSON {
				var innerJSON interface{}
				if err := json.Unmarshal([]byte(logEntry.Message), &innerJSON); err != nil {
					if *debugMode {
						fmt.Fprintf(os.Stderr, "Invalid inner JSON: %v\n", err)
						fmt.Fprintf(os.Stderr, "First 100 chars: %s\n", 
							logEntry.Message[:min(100, len(logEntry.Message))])
					}
					invalidRecords++
					continue
				}
			}
			
			validRecords++
			
			// Output based on pretty-print option
			if *prettyPrint {
				var innerJSON interface{}
				if err := json.Unmarshal([]byte(logEntry.Message), &innerJSON); err != nil {
					// This should never happen if validation is enabled
					fmt.Fprintf(os.Stderr, "Error parsing inner JSON: %v\n", err)
					continue
				}
				
				prettyBytes, err := json.MarshalIndent(innerJSON, "", "  ")
				if err != nil {
					fmt.Fprintf(os.Stderr, "Error formatting JSON: %v\n", err)
					continue
				}
				
				fmt.Fprintln(output, string(prettyBytes))
			} else {
				// Just output the inner message as-is
				fmt.Fprintln(output, logEntry.Message)
			}
		} else {
			if *debugMode {
				fmt.Fprintf(os.Stderr, "Empty @message field in record %d\n", i+1)
			}
			skippedRecords++
		}
	}

	// Print summary to stderr
	fmt.Fprintf(os.Stderr, "Processing summary:\n")
	fmt.Fprintf(os.Stderr, "- Total JSON objects found: %d\n", len(objectStarts))
	fmt.Fprintf(os.Stderr, "- Successfully processed: %d records\n", processedRecords)
	fmt.Fprintf(os.Stderr, "- Valid @message fields: %d\n", validRecords)
	fmt.Fprintf(os.Stderr, "- Invalid @message fields: %d\n", invalidRecords)
	fmt.Fprintf(os.Stderr, "- Skipped records: %d\n", skippedRecords)
}