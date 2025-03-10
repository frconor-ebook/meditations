#!/bin/bash
#
# FRCMED Markdown Preprocessing Suite
# This script automates the conversion and processing of transcripts
# from DocX to Markdown format with standardized naming and content.
#
# Usage: ./preprocess_files.sh [OPTIONS]
#
# Options:
#   -v, --verbose    Enable verbose output
#   -s, --skip-step  Skip specific step (download|convert|standardize|process)
#   -h, --help       Display this help message
#   -l, --log        Create a log file with detailed output

# Script configuration
set -o pipefail  # Ensure pipeline errors are caught
SCRIPT_VERSION="1.2.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)/.."
START_TIME=$(date +%s)
LOG_FILE=""
VERBOSE=false
SKIP_DOWNLOAD=false
SKIP_CONVERT=false
SKIP_STANDARDIZE=false
SKIP_PROCESS=false

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display the script's usage information
show_help() {
    echo -e "${BLUE}FRCMED Markdown Preprocessing Suite${NC} v${SCRIPT_VERSION}"
    echo
    echo "This script automates the conversion and processing of medical transcripts"
    echo "from DocX to Markdown format with standardized naming and content."
    echo
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo
    echo "Options:"
    echo "  -v, --verbose         Enable verbose output"
    echo "  -s, --skip-step STEP  Skip specific step (download|convert|standardize|process)"
    echo "  -l, --log FILE        Write output to log file"
    echo "  -h, --help            Display this help message"
    echo
    echo "Example:"
    echo "  $(basename "$0") --verbose --log preprocess.log"
    echo "  $(basename "$0") --skip-step convert"
}

# Function to display log messages with timestamp
log() {
    local level=$1
    local message=$2
    local color=$NC
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")

    case $level in
        INFO)    color=$BLUE ;;
        SUCCESS) color=$GREEN ;;
        WARNING) color=$YELLOW ;;
        ERROR)   color=$RED ;;
    esac

    echo -e "[${timestamp}] ${color}${level}${NC}: ${message}"

    # If log file is specified, write to it without colors
    if [[ -n "$LOG_FILE" ]]; then
        echo -e "[${timestamp}] ${level}: ${message}" >> "$LOG_FILE"
    fi
}

# Function to display error messages and exit the script
error_message() {
    log "ERROR" "$1"

    # Show additional debug info in verbose mode
    if [[ "$VERBOSE" = true ]]; then
        log "ERROR" "Command that failed: $BASH_COMMAND"
        log "ERROR" "Working directory: $(pwd)"
        log "ERROR" "Exit code: $?"
    fi

    log "ERROR" "Preprocessing failed. Exiting."
    exit 1
}

# Function to display verbose information
verbose() {
    if [[ "$VERBOSE" = true ]]; then
        log "INFO" "$1"
    fi
}

# Function to check for required tools
check_dependencies() {
    local missing_deps=false

    log "INFO" "Checking dependencies..."

    # Check for required commands
    for cmd in python3 find; do
        if ! command -v $cmd &> /dev/null; then
            log "ERROR" "Required command not found: $cmd"
            missing_deps=true
        else
            verbose "Found dependency: $cmd $(command -v $cmd)"
        fi
    done

    # Check for script dependencies
    local script_deps=(
        "$BASE_DIR/meditations/download_from_dropbox.py"
        "$BASE_DIR/meditations/preprocessing_scripts/convert_all_to_md_with_progress_parallel.sh"
        "$BASE_DIR/meditations/preprocessing_scripts/standardize_filename.py"
        "$BASE_DIR/meditations/process_markdown.py"
    )

    for script in "${script_deps[@]}"; do
        if [[ ! -f "$script" ]]; then
            log "ERROR" "Required script not found: $script"
            missing_deps=true
        else
            verbose "Found script: $script"

            # Check if script is executable (for bash scripts)
            if [[ "$script" == *.sh ]] && [[ ! -x "$script" ]]; then
                log "WARNING" "Script is not executable: $script. Attempting to fix..."
                chmod +x "$script" || {
                    log "ERROR" "Failed to make script executable: $script"
                    missing_deps=true
                }
            fi
        fi
    done

    if [[ "$missing_deps" = true ]]; then
        error_message "Missing dependencies. Please install required tools and ensure scripts exist."
    else
        log "SUCCESS" "All dependencies found."
    fi
}

# Function to display elapsed time
show_elapsed_time() {
    local end_time=$(date +%s)
    local elapsed=$((end_time - START_TIME))
    local hours=$((elapsed / 3600))
    local minutes=$(( (elapsed % 3600) / 60 ))
    local seconds=$((elapsed % 60))

    log "INFO" "Total execution time: ${hours}h ${minutes}m ${seconds}s"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            -s|--skip-step)
                case $2 in
                    download)
                        SKIP_DOWNLOAD=true
                        ;;
                    convert)
                        SKIP_CONVERT=true
                        ;;
                    standardize)
                        SKIP_STANDARDIZE=true
                        ;;
                    process)
                        SKIP_PROCESS=true
                        ;;
                    *)
                        log "ERROR" "Unknown skip step: $2"
                        show_help
                        exit 1
                        ;;
                esac
                shift 2
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Initialize log file if specified
    if [[ -n "$LOG_FILE" ]]; then
        echo "# FRCMED Preprocessing Log - $(date)" > "$LOG_FILE"
        log "INFO" "Logging to file: $LOG_FILE"
    fi
}

# Function to download files from Dropbox
download_from_dropbox() {
    if [[ "$SKIP_DOWNLOAD" = true ]]; then
        log "WARNING" "Skipping Dropbox download as requested."
        return 0
    fi

    log "INFO" "Downloading files from Dropbox..."

    # Change to the meditations directory
    cd "$BASE_DIR/meditations" || error_message "Could not change to meditations directory."

    # Execute the Python download script
    python3 download_from_dropbox.py || error_message "Failed to download files from Dropbox."

    log "SUCCESS" "Files have been downloaded from Dropbox."
}

# Function to convert DocX to Markdown
convert_to_markdown() {
    if [[ "$SKIP_CONVERT" = true ]]; then
        log "WARNING" "Skipping DocX to Markdown conversion as requested."
        return 0
    fi

    log "INFO" "Converting DocX to Markdown..."

    # Change directory to where the conversion script is located
    cd "$BASE_DIR/meditations/preprocessing_scripts/" || error_message "Could not change to preprocessing_scripts directory."

    # Check if the script exists and is executable
    if [[ ! -f "./convert_all_to_md_with_progress_parallel.sh" ]]; then
        error_message "Conversion script not found: convert_all_to_md_with_progress_parallel.sh"
    fi

    log "INFO" "Starting conversion (this may take a while)..."

    # Execute with timing information
    local start_time=$(date +%s)

    # Run the conversion script
    ./convert_all_to_md_with_progress_parallel.sh || error_message "DocX to Markdown conversion failed."

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log "SUCCESS" "Conversion completed in ${duration} seconds."
}

# Function to standardize filenames
standardize_filenames() {
    if [[ "$SKIP_STANDARDIZE" = true ]]; then
        log "WARNING" "Skipping filename standardization as requested."
        return 0
    fi

    log "INFO" "Standardizing filenames..."

    # We're already in the preprocessing_scripts directory from the previous step
    if [[ ! -f "./standardize_filename.py" ]]; then
        error_message "Standardization script not found: standardize_filename.py"
    fi

    # Execute the Python script
    python standardize_filename.py || error_message "Filename standardization failed."

    log "SUCCESS" "Filenames have been standardized."
}

# Function to process markdown files
process_markdown() {
    if [[ "$SKIP_PROCESS" = true ]]; then
        log "WARNING" "Skipping Markdown processing as requested."
        return 0
    fi

    log "INFO" "Processing Markdown files..."

    # Change directory to the meditations directory
    cd "$BASE_DIR/meditations" || error_message "Could not change to meditations directory."

    # Check if the script exists
    if [[ ! -f "./process_markdown.py" ]]; then
        error_message "Processing script not found: process_markdown.py"
    fi

    # Execute the Python script
    python process_markdown.py || error_message "Markdown processing failed."

    log "SUCCESS" "Markdown files have been processed."
}

# Main function to run the entire preprocessing workflow
main() {
    trap 'error_message "Script interrupted."' INT TERM

    log "INFO" "Starting FRCMED preprocessing workflow v${SCRIPT_VERSION}"
    verbose "Base directory: $BASE_DIR"
    verbose "Script directory: $SCRIPT_DIR"

    # Check dependencies before proceeding
    check_dependencies

    # Run the preprocessing steps
    download_from_dropbox   # Added as the first step
    convert_to_markdown
    standardize_filenames
    process_markdown

    # Display summary
    log "SUCCESS" "All preprocessing steps completed successfully."
    show_elapsed_time

    exit 0
}

# Parse arguments before running main
parse_args "$@"

# Run the main function
main