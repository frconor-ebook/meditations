#!/bin/bash

# Ultra-compatible macOS parallel conversion wrapper for convert_fast.sh
# Processes multiple files simultaneously for faster conversion
# Supports incremental processing - only converts changed files
#
# Usage: ./convert_all_to_md_with_progress_parallel.sh [--force]
#   --force: Force conversion of all files (ignore change detection)

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Parent directory is upload_frcmed_to_web (one level up from preprocessing_scripts, then one more from meditations)
PARENT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Meditations directory (for manifest)
MEDITATIONS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse command line arguments
FORCE_MODE=false
for arg in "$@"; do
    case $arg in
        --force|-f)
            FORCE_MODE=true
            shift
            ;;
    esac
done

# Set the source and destination directories dynamically
source_dir="$PARENT_DIR/transcript_proofread_MSWord"
dest_dir="$PARENT_DIR/transcript_proofread_markdown"

# Path to the conversion script
CONVERT_SCRIPT="./convert_fast.sh"

# Path to the change detection helper
CHECK_CHANGED="./check_changed_files.py"

# Ensure the destination directory exists (but don't delete it for incremental mode)
mkdir -p "$dest_dir"

# Check if we should use incremental mode
if [ "$FORCE_MODE" = true ]; then
    echo "Force mode: Converting all files..."
    # In force mode, clear the destination directory
    rm -rf "$dest_dir"
    mkdir -p "$dest_dir"
fi

# Determine number of CPU cores for optimal parallelism (macOS specific)
NUM_CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
MAX_JOBS=$(( NUM_CORES * 3 / 4 ))
[ $MAX_JOBS -lt 1 ] && MAX_JOBS=1

echo "Using $MAX_JOBS parallel processes on macOS"

# Use the current directory for logs
LOG_DIR="./conversion_logs"
mkdir -p "$LOG_DIR"

# Status tracking files
success_log="$LOG_DIR/success.log"
error_log="$LOG_DIR/error.log"
job_count_file="$LOG_DIR/job_count.txt"

# Clear previous logs
echo "0" > "$job_count_file"
> "$success_log"
> "$error_log"

# Get list of files to process
echo "Finding files to process..."
all_files=()

if [ "$FORCE_MODE" = true ]; then
    # Force mode: process all files
    while IFS= read -r file; do
        all_files+=("$file")
    done < <(find "$source_dir" -name "*.doc*")
    total=${#all_files[@]}
    echo "Force mode: Found $total files to process"
else
    # Incremental mode: only process changed files
    echo "Checking for changed files..."

    # Get files to convert using the Python helper
    if [ -f "$CHECK_CHANGED" ]; then
        # Get count first
        count_output=$(python3 "$CHECK_CHANGED" "$source_dir" "$dest_dir" --manifest-dir "$MEDITATIONS_DIR" --output count 2>/dev/null)
        echo "$count_output"

        # Delete removed files first
        while IFS= read -r md_file; do
            if [ -n "$md_file" ] && [ -f "$dest_dir/$md_file" ]; then
                echo "Removing deleted file: $md_file"
                rm -f "$dest_dir/$md_file"
            fi
        done < <(python3 "$CHECK_CHANGED" "$source_dir" "$dest_dir" --manifest-dir "$MEDITATIONS_DIR" --output delete 2>/dev/null)

        # Get files to convert
        while IFS= read -r filename; do
            if [ -n "$filename" ]; then
                all_files+=("$source_dir/$filename")
            fi
        done < <(python3 "$CHECK_CHANGED" "$source_dir" "$dest_dir" --manifest-dir "$MEDITATIONS_DIR" --output convert 2>/dev/null)
    else
        echo "Warning: check_changed_files.py not found, falling back to full conversion"
        while IFS= read -r file; do
            all_files+=("$file")
        done < <(find "$source_dir" -name "*.doc*")
    fi

    total=${#all_files[@]}
    if [ $total -eq 0 ]; then
        echo "No files need conversion. All files are up to date."
        # Update the manifest anyway
        python3 "$CHECK_CHANGED" "$source_dir" "$dest_dir" --manifest-dir "$MEDITATIONS_DIR" --output update-manifest 2>/dev/null
        exit 0
    fi
    echo "Found $total files to convert"
fi

# Create directory for status tracking
STATUS_DIR="$LOG_DIR/status"
mkdir -p "$STATUS_DIR"
rm -f "$STATUS_DIR"/*

# Function to convert a single file
convert_file() {
    local doc_file="$1"
    local file_id="$2"
    local markdown_file="$dest_dir/$(basename "$doc_file" | sed 's/\.doc[x]*$/.md/')"
    local status_file="$STATUS_DIR/$file_id"

    # Convert the file
    if "$CONVERT_SCRIPT" "$doc_file" > "$markdown_file" 2>/dev/null; then
        echo "✓ $(basename "$doc_file")" > "$status_file.success"
    else
        echo "✗ $(basename "$doc_file")" > "$status_file.error"
    fi

    # Update job count atomically
    local count=$(cat "$job_count_file" 2>/dev/null || echo "1")
    # Ensure it's numeric
    if [[ ! "$count" =~ ^[0-9]+$ ]]; then
        count=1
    fi
    echo $((count - 1)) > "$job_count_file"
}

# Track number of completed files
completed=0

# Function to update progress display
update_progress() {
    # Count successful and failed conversions
    local success_count=$(ls "$STATUS_DIR"/*.success 2>/dev/null | wc -l | tr -d ' ' || echo 0)
    local error_count=$(ls "$STATUS_DIR"/*.error 2>/dev/null | wc -l | tr -d ' ' || echo 0)
    local current_completed=$((success_count + error_count))

    # Update the display if the count has changed
    if [ $current_completed -ne $completed ]; then
        completed=$current_completed
        percent=$(( completed * 100 / total ))
        printf "\rProgress: [%-50s] %d%% (%d/%d)" \
            "$(printf '#%.0s' $(seq 1 $(( percent / 2 ))))" \
            "$percent" "$completed" "$total"

        # Update the summary logs
        if [ $success_count -gt 0 ]; then
            cat "$STATUS_DIR"/*.success > "$success_log" 2>/dev/null
        fi
        if [ $error_count -gt 0 ]; then
            cat "$STATUS_DIR"/*.error > "$error_log" 2>/dev/null
        fi
    fi
}

# Process files in parallel
for i in "${!all_files[@]}"; do
    # Wait if we've reached the maximum number of background jobs
    current_jobs=$(cat "$job_count_file" 2>/dev/null || echo "0")
    # Ensure it's numeric
    if [[ ! "$current_jobs" =~ ^[0-9]+$ ]]; then
        current_jobs=0
    fi

    while [ $current_jobs -ge $MAX_JOBS ]; do
        update_progress
        sleep 0.1
        current_jobs=$(cat "$job_count_file" 2>/dev/null || echo "0")
        # Ensure it's numeric
        if [[ ! "$current_jobs" =~ ^[0-9]+$ ]]; then
            current_jobs=0
        fi
    done

    # Increment job count
    echo $((current_jobs + 1)) > "$job_count_file"

    # Start conversion in background
    (
        convert_file "${all_files[$i]}" "$i"
    ) &

    # Update progress every 5 files
    if [ $((i % 5)) -eq 0 ] || [ $i -eq $((total - 1)) ]; then
        update_progress
    fi
done

# Monitor for completion
echo
echo "Waiting for remaining jobs to complete..."
timeout_counter=0
max_timeout=60 # 60 seconds max wait

while [ $timeout_counter -lt $max_timeout ]; do
    # Read the count safely with a default value if empty
    count=$(cat "$job_count_file" 2>/dev/null || echo "0")
    # Ensure count is numeric
    if [[ ! "$count" =~ ^[0-9]+$ ]]; then
        count=0
    fi

    # Count successful and failed conversions
    success_count=$(ls "$STATUS_DIR"/*.success 2>/dev/null | wc -l | tr -d ' ' || echo 0)
    error_count=$(ls "$STATUS_DIR"/*.error 2>/dev/null | wc -l | tr -d ' ' || echo 0)
    current_completed=$((success_count + error_count))

    # Check if all files have been processed regardless of job count
    if [ $current_completed -ge $total ]; then
        # All files processed, we can exit the loop
        break
    fi

    # Check if job count shows we're done
    if [ $count -le 0 ]; then
        break
    fi

    update_progress
    sleep 1
    timeout_counter=$((timeout_counter + 1))
done

# Only show timeout warning if we actually have incomplete conversions
success_count=$(ls "$STATUS_DIR"/*.success 2>/dev/null | wc -l | tr -d ' ' || echo 0)
error_count=$(ls "$STATUS_DIR"/*.error 2>/dev/null | wc -l | tr -d ' ' || echo 0)
current_completed=$((success_count + error_count))

if [ $timeout_counter -ge $max_timeout ] && [ $current_completed -lt $total ]; then
    echo "Timeout reached. Some jobs may not have completed."
    # Force terminate any remaining background processes
    pkill -P $$ 2>/dev/null || true
fi

# Final update of progress
update_progress

# Final statistics using ls instead of find
success_count=$(ls "$STATUS_DIR"/*.success 2>/dev/null | wc -l | tr -d ' ' || echo 0)
error_count=$(ls "$STATUS_DIR"/*.error 2>/dev/null | wc -l | tr -d ' ' || echo 0)

echo
echo "Conversion complete!"
echo "Successfully converted: $success_count files"
echo "Failed conversions: $error_count files"

# Display missing files if any
if [ $((success_count + error_count)) -lt $total ]; then
    echo "Warning: $(($total - success_count - error_count)) files may not have been processed!"
fi

# List failed files if any
if [ $error_count -gt 0 ]; then
    echo "Files that failed to convert:"
    cat "$error_log"
fi

# Clean up status directory
rm -rf "$STATUS_DIR"
rm -f "$job_count_file"

# Update the manifest with new hashes
if [ -f "$CHECK_CHANGED" ]; then
    echo "Updating file manifest..."
    python3 "$CHECK_CHANGED" "$source_dir" "$dest_dir" --manifest-dir "$MEDITATIONS_DIR" --output update-manifest 2>/dev/null
fi

echo "All done!"
exit 0