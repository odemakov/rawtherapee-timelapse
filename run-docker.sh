#!/bin/bash

# Wrapper script for running RawTherapee in Docker

# Default values
INPUT_DIR=""
OUTPUT_DIR=""
SERVICE="rawtherapee"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            INPUT_DIR="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -i, --input DIR      Input directory (default: ./input)"
            echo "  -o, --output DIR     Output directory (default: ./output)"
            echo "  -s, --service NAME   Service to run (default: rawtherapee)"
            echo ""
            echo "Available services:"
            echo "  rawtherapee-shell    Interactive shell"
            echo "  rawtherapee         Process all files with RawTherapee CLI"
            echo "  timelapse           Run rawtherapee-timelapse interpolation"
            echo ""
            echo "Examples:"
            echo "  $0 -i /path/to/raw/files -o /path/to/output"
            echo "  $0 -i ~/Photos/timelapse -s timelapse"
            echo "  $0 -i ./my-images -o ./processed -s rawtherapee"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Convert relative paths to absolute paths
if [[ -n "$INPUT_DIR" ]]; then
    INPUT_DIR=$(cd "$INPUT_DIR" 2>/dev/null && pwd) || {
        echo "Error: Input directory '$INPUT_DIR' does not exist"
        exit 1
    }
fi

if [[ -n "$OUTPUT_DIR" ]]; then
    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"
    OUTPUT_DIR=$(cd "$OUTPUT_DIR" && pwd)
fi

# Export environment variables
export INPUT_DIR
export OUTPUT_DIR

# Run the selected service
echo "Running service: $SERVICE"
echo "Input directory: ${INPUT_DIR:-./input}"
echo "Output directory: ${OUTPUT_DIR:-./output}"
echo ""

docker compose run --rm "$SERVICE"
