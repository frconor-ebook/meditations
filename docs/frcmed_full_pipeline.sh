#!/bin/bash
#
# FRCMED Markdown Preprocessing Suite
# This script automates the conversion and processing of transcripts
# from DocX to Markdown format with standardized naming and content.
#
# Usage: ./frcmed_full_pipeline.sh  [OPTIONS]
#
# Options:
#   -v, --verbose     Enable verbose output
#   -s, --skip-step   Skip specific step(s) (download|convert|standardize|process|build|deploy)
#   -i, --include-step Only run specific step(s) (download|convert|standardize|process|build|deploy)
#   -f, --force       Force full processing (ignore incremental change detection)
#   -h, --help        Display this help message
#   -l, --log         Create a log file with detailed output

# Script configuration
set -o pipefail  # Ensure pipeline errors are caught
SCRIPT_VERSION="1.6.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$SCRIPT_DIR"  # Changed: Use script directory as base directory
PARENT_DIR="$(cd "$(dirname "$0")" && pwd)/.."
START_TIME=$(date +%s)
LOG_FILE=""
VERBOSE=false
COMMIT_MESSAGE=""
FORCE_MODE=false

# Initialize rbenv to use the correct Ruby version
eval "$(rbenv init -)" 2>/dev/null || true

# Skip flags
SKIP_DOWNLOAD=false
SKIP_CONVERT=false
SKIP_STANDARDIZE=false
SKIP_PROCESS=false
SKIP_BUILD=false
SKIP_DEPLOY=false

# Include flags
INCLUDE_DOWNLOAD=false
INCLUDE_CONVERT=false
INCLUDE_STANDARDIZE=false
INCLUDE_PROCESS=false
INCLUDE_BUILD=false
INCLUDE_DEPLOY=false
INCLUDE_ANY=false  # Track if any include flags are set

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
    echo "It also builds the Jekyll site and deploys to GitHub Pages."
    echo
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo
    echo "Options:"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -s, --skip-step STEPS   Skip specific step(s) (comma-separated list)"
    echo "                          Valid steps: download,convert,standardize,process,build,deploy"
    echo "  -i, --include-step STEPS Only run specific step(s) (comma-separated list)"
    echo "                          Valid steps: download,convert,standardize,process,build,deploy"
    echo "  -f, --force             Force full processing (ignore incremental change detection)"
    echo "  -m, --message MSG       Custom git commit message (optional)"
    echo "  -l, --log FILE          Write output to log file"
    echo "  -h, --help              Display this help message"
    echo
    echo "Examples:"
    echo "  $(basename "$0") --verbose --log pipeline.log"
    echo "  $(basename "$0") --skip-step convert"
    echo "  $(basename "$0") --skip-step build,deploy"
    echo "  $(basename "$0") --include-step download,process"
    echo "  $(basename "$0") --include-step build,deploy"
    echo "  $(basename "$0") -i build  # Short form for --include-step"
    echo "  $(basename "$0") --include-step deploy -m \"Fix footer styling\""
    echo "  $(basename "$0") --message \"Improve typography\" --include-step build,deploy"
    echo "  $(basename "$0") --force  # Force full reprocessing of all files"
    echo
    echo "Note: --include-step and --skip-step cannot be used together"
    echo
    echo "Incremental Processing:"
    echo "  By default, the pipeline uses incremental processing to only download,"
    echo "  convert, and process files that have changed. Use --force to override"
    echo "  this behavior and process all files."
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

# Function to set a skip flag based on step name
set_skip_flag() {
    local step=$1
    case $step in
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
        build)
            SKIP_BUILD=true
            ;;
        deploy)
            SKIP_DEPLOY=true
            ;;
        *)
            log "ERROR" "Unknown skip step: $step"
            show_help
            exit 1
            ;;
    esac
}

# Function to set an include flag based on step name
set_include_flag() {
    local step=$1
    INCLUDE_ANY=true
    case $step in
        download)
            INCLUDE_DOWNLOAD=true
            ;;
        convert)
            INCLUDE_CONVERT=true
            ;;
        standardize)
            INCLUDE_STANDARDIZE=true
            ;;
        process)
            INCLUDE_PROCESS=true
            ;;
        build)
            INCLUDE_BUILD=true
            ;;
        deploy)
            INCLUDE_DEPLOY=true
            ;;
        *)
            log "ERROR" "Unknown include step: $step"
            show_help
            exit 1
            ;;
    esac
}

# Function to check for required tools
check_dependencies() {
    local missing_deps=false

    log "INFO" "Checking dependencies..."

    # Check for required commands
    for cmd in python3 find bundle git; do
        if ! command -v $cmd &> /dev/null; then
            log "ERROR" "Required command not found: $cmd"
            missing_deps=true
        else
            verbose "Found dependency: $cmd $(command -v $cmd)"
        fi
    done

    # Check for script dependencies
    local script_deps=(
        "$BASE_DIR/download_from_dropbox.py"
        "$BASE_DIR/preprocessing_scripts/convert_all_to_md_with_progress_parallel.sh"
        "$BASE_DIR/preprocessing_scripts/standardize_filename.py"
        "$BASE_DIR/process_markdown.py"
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
    local skip_used=false
    local include_used=false

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
            -f|--force)
                FORCE_MODE=true
                shift
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            -m|--message)
                COMMIT_MESSAGE="$2"
                shift 2
                ;;
            -s|--skip-step)
                skip_used=true
                if [[ "$include_used" = true ]]; then
                    log "ERROR" "Cannot use --skip-step and --include-step together"
                    show_help
                    exit 1
                fi

                # Split the comma-separated list into an array
                IFS=',' read -ra STEPS <<< "$2"

                # Process each step in the list
                for step in "${STEPS[@]}"; do
                    set_skip_flag "$step"
                done

                shift 2
                ;;
            -i|--include-step)
                include_used=true
                if [[ "$skip_used" = true ]]; then
                    log "ERROR" "Cannot use --skip-step and --include-step together"
                    show_help
                    exit 1
                fi

                # Split the comma-separated list into an array
                IFS=',' read -ra STEPS <<< "$2"

                # Process each step in the list
                for step in "${STEPS[@]}"; do
                    set_include_flag "$step"
                done

                shift 2
                ;;
            # Handle short form include option without parameter
            -i*)
                include_used=true
                if [[ "$skip_used" = true ]]; then
                    log "ERROR" "Cannot use --skip-step and --include-step together"
                    show_help
                    exit 1
                fi

                # Extract the value directly from the argument
                local arg="${1:2}"

                # Split the comma-separated list into an array
                IFS=',' read -ra STEPS <<< "$arg"

                # Process each step in the list
                for step in "${STEPS[@]}"; do
                    set_include_flag "$step"
                done

                shift
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
    if [[ "$INCLUDE_ANY" = true && "$INCLUDE_DOWNLOAD" = false ]]; then
        log "INFO" "Skipping Dropbox download (not included in specified steps)."
        return 0
    fi

    if [[ "$SKIP_DOWNLOAD" = true ]]; then
        log "WARNING" "Skipping Dropbox download as requested."
        return 0
    fi

    log "INFO" "Downloading files from Dropbox..."

    # Change to the base directory
    cd "$BASE_DIR" || error_message "Could not change to base directory."

    # Build command with optional --force flag
    local download_cmd="python3 download_from_dropbox.py"
    if [[ "$FORCE_MODE" = true ]]; then
        download_cmd="$download_cmd --force"
        verbose "Force mode enabled for download"
    fi

    # Execute the Python download script
    $download_cmd || error_message "Failed to download files from Dropbox."

    log "SUCCESS" "Files have been downloaded from Dropbox."
}

# Function to convert DocX to Markdown
convert_to_markdown() {
    if [[ "$INCLUDE_ANY" = true && "$INCLUDE_CONVERT" = false ]]; then
        log "INFO" "Skipping DocX to Markdown conversion (not included in specified steps)."
        return 0
    fi

    if [[ "$SKIP_CONVERT" = true ]]; then
        log "WARNING" "Skipping DocX to Markdown conversion as requested."
        return 0
    fi

    log "INFO" "Converting DocX to Markdown..."

    # Change directory to where the conversion script is located
    cd "$BASE_DIR/preprocessing_scripts/" || error_message "Could not change to preprocessing_scripts directory."

    # Check if the script exists and is executable
    if [[ ! -f "./convert_all_to_md_with_progress_parallel.sh" ]]; then
        error_message "Conversion script not found: convert_all_to_md_with_progress_parallel.sh"
    fi

    log "INFO" "Starting conversion (this may take a while)..."

    # Execute with timing information
    local start_time=$(date +%s)

    # Build command with optional --force flag
    local convert_cmd="./convert_all_to_md_with_progress_parallel.sh"
    if [[ "$FORCE_MODE" = true ]]; then
        convert_cmd="$convert_cmd --force"
        verbose "Force mode enabled for conversion"
    fi

    # Run the conversion script
    $convert_cmd || error_message "DocX to Markdown conversion failed."

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log "SUCCESS" "Conversion completed in ${duration} seconds."
}

# Function to standardize filenames
standardize_filenames() {
    if [[ "$INCLUDE_ANY" = true && "$INCLUDE_STANDARDIZE" = false ]]; then
        log "INFO" "Skipping filename standardization (not included in specified steps)."
        return 0
    fi

    if [[ "$SKIP_STANDARDIZE" = true ]]; then
        log "WARNING" "Skipping filename standardization as requested."
        return 0
    fi

    log "INFO" "Standardizing filenames..."

    # Always change to the preprocessing_scripts directory
    # This ensures we're in the right place regardless of whether previous steps were run
    cd "$BASE_DIR/preprocessing_scripts/" || error_message "Could not change to preprocessing_scripts directory."

    # Check if the script exists
    if [[ ! -f "./standardize_filename.py" ]]; then
        error_message "Standardization script not found: standardize_filename.py"
    fi

    # Execute the Python script
    python3 standardize_filename.py || error_message "Filename standardization failed."

    log "SUCCESS" "Filenames have been standardized."
}

# Function to process markdown files
process_markdown() {
    if [[ "$INCLUDE_ANY" = true && "$INCLUDE_PROCESS" = false ]]; then
        log "INFO" "Skipping Markdown processing (not included in specified steps)."
        return 0
    fi

    if [[ "$SKIP_PROCESS" = true ]]; then
        log "WARNING" "Skipping Markdown processing as requested."
        return 0
    fi

    log "INFO" "Processing Markdown files..."

    # Always change to the base directory
    cd "$BASE_DIR" || error_message "Could not change to base directory."

    # Check if the script exists
    if [[ ! -f "./process_markdown.py" ]]; then
        error_message "Processing script not found: process_markdown.py"
    fi

    # Build command with optional --force flag
    local process_cmd="python3 process_markdown.py"
    if [[ "$FORCE_MODE" = true ]]; then
        process_cmd="$process_cmd --force"
        verbose "Force mode enabled for processing"
    fi

    # Execute the Python script
    $process_cmd || error_message "Markdown processing failed."

    log "SUCCESS" "Markdown files have been processed."
}

# Function to build the Jekyll site
build_jekyll_site() {
    if [[ "$INCLUDE_ANY" = true && "$INCLUDE_BUILD" = false ]]; then
        log "INFO" "Skipping Jekyll build (not included in specified steps)."
        return 0
    fi

    if [[ "$SKIP_BUILD" = true ]]; then
        log "WARNING" "Skipping Jekyll build as requested."
        return 0
    fi

    log "INFO" "Building Jekyll site..."

    # Change directory to the base directory where Jekyll is set up
    cd "$BASE_DIR" || error_message "Could not change to base directory."

    # Clean the Jekyll site
    log "INFO" "Cleaning Jekyll site..."
    bundle exec jekyll clean || error_message "Jekyll clean failed."

    # Build the Jekyll site
    log "INFO" "Building Jekyll site..."
    bundle exec jekyll build || error_message "Jekyll build failed."

    log "SUCCESS" "Jekyll site has been built."
}

# Function to deploy to GitHub Pages
deploy_to_github() {
    if [[ "$INCLUDE_ANY" = true && "$INCLUDE_DEPLOY" = false ]]; then
        log "INFO" "Skipping GitHub deployment (not included in specified steps)."
        return 0
    fi

    if [[ "$SKIP_DEPLOY" = true ]]; then
        log "WARNING" "Skipping GitHub deployment as requested."
        return 0
    fi

    log "INFO" "Deploying to GitHub Pages..."

    # Change directory to the base directory where the git repo is
    cd "$BASE_DIR" || error_message "Could not change to base directory."

    # Check if git is initialized
    if [ ! -d ".git" ]; then
        log "ERROR" "Git repository not found. Cannot deploy to GitHub Pages."
        return 1
    fi

    # Add all files to git
    log "INFO" "Adding files to git..."
    git add . || error_message "Git add failed."

    # Commit changes
    # Use custom message if provided, otherwise use default
    if [[ -n "$COMMIT_MESSAGE" ]]; then
        local commit_message="$COMMIT_MESSAGE"
        verbose "Using custom commit message: $commit_message"
    else
        local commit_message="Update with latest edits (automated commit from frcmed_full_pipeline.sh)"
        verbose "Using default commit message"
    fi

    log "INFO" "Committing changes..."
    git commit -m "$commit_message" || {
        # If there's nothing to commit, this is not an error
        if [[ "$?" -eq 1 && $(git status --porcelain) == "" ]]; then
            log "WARNING" "No changes to commit. Skipping git commit."
        else
            error_message "Git commit failed."
        fi
    }

    # Force push to GitHub (safe for auto-generated content where local is always the source of truth)
    log "INFO" "Pushing to GitHub..."
    git push --force origin main || error_message "Git push failed."

    log "SUCCESS" "Site has been deployed to GitHub Pages."
}

# Function to check if Jekyll can run in current directory
check_jekyll_environment() {
    local has_gemfile=false
    local has_config=false

    if [[ -f "Gemfile" ]]; then
        has_gemfile=true
        verbose "Found Gemfile in $(pwd)"
    fi

    if [[ -f "_config.yml" ]]; then
        has_config=true
        verbose "Found _config.yml in $(pwd)"
    fi

    if [[ "$has_gemfile" = false || "$has_config" = false ]]; then
        log "WARNING" "Jekyll files not found in current directory. This might cause issues with build and deploy steps."
        verbose "Gemfile found: $has_gemfile"
        verbose "Config found: $has_config"
    fi
}

# Main function to run the entire preprocessing workflow
main() {
    trap 'error_message "Script interrupted."' INT TERM

    log "INFO" "Starting FRCMED full pipeline workflow v${SCRIPT_VERSION}"
    verbose "Base directory: $BASE_DIR"
    verbose "Script directory: $SCRIPT_DIR"

    if [[ "$FORCE_MODE" = true ]]; then
        log "INFO" "Force mode enabled - will process all files regardless of changes"
    else
        log "INFO" "Incremental mode - will only process changed files"
    fi

    # Check Jekyll environment before proceeding
    check_jekyll_environment

    # Check dependencies before proceeding
    check_dependencies

    # Run the preprocessing steps
    download_from_dropbox
    convert_to_markdown
    standardize_filenames
    process_markdown
    build_jekyll_site
    deploy_to_github

    # Display summary
    log "SUCCESS" "All pipeline steps completed successfully."
    show_elapsed_time

    exit 0
}

# Parse arguments before running main
parse_args "$@"

# Run the main function
main