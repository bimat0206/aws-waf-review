#!/bin/bash

# ✅ Define paths (Modify as needed)
PARSE_WAF_LOGS_EXEC="./waf_logs_parser"  # Path to parsing executable
DEFAULT_INPUT_DIR="../logs/raw/manh-acfc/acfc-common-acl-1"           # Default input directory for logs
DEFAULT_OUTPUT_DIR="../logs/processed-acfc"       # Default output directory for parsed logs

# ✅ Ask the user for input directory
read -p "Enter the input directory containing CloudWatch logs (default: $DEFAULT_INPUT_DIR): " INPUT_DIR
INPUT_DIR=${INPUT_DIR:-"$DEFAULT_INPUT_DIR"}  # Use default if empty

# ✅ Ask the user for output directory
read -p "Enter the output directory for parsed logs (default: $DEFAULT_OUTPUT_DIR): " OUTPUT_DIR
OUTPUT_DIR=${OUTPUT_DIR:-"$DEFAULT_OUTPUT_DIR"}  # Use default if empty
mkdir -p "$OUTPUT_DIR"  # Ensure output directory exists

# ✅ Verify input directory exists
if [[ ! -d "$INPUT_DIR" ]]; then
    echo "Error: Input directory '$INPUT_DIR' does not exist."
    exit 1
fi

# ✅ Find and process all JSON log files
log_files=("$INPUT_DIR"/*.json)
if [[ ${#log_files[@]} -eq 0 ]]; then
    echo "No JSON log files found in $INPUT_DIR."
    exit 1
fi

echo "Processing ${#log_files[@]} log files from $INPUT_DIR..."
for log_file in "$INPUT_DIR"/*.json; do
    output_file="$OUTPUT_DIR/$(basename "${log_file%.json}_parsed.json")"
    echo "Parsing: $log_file -> $output_file"
    
    # ✅ Run the log parser for each file pretty printing
    $PARSE_WAF_LOGS_EXEC -input "$log_file" -output "$output_file"

    echo "Parsed logs saved to: $output_file"
done

echo "✅ Batch log parsing completed. Parsed files are in $OUTPUT_DIR."
