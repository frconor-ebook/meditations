#!/bin/bash

# Ultra-compatible macOS parallel conversion wrapper for convert_fast.sh
# Processes multiple files simultaneously for faster conversion
# This has been tested and it works! It's just that you have to be patient at the end of the process.
# The script will wait for the remaining jobs to complete before displaying the final statistics.

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown"

# Path to the conversion script
CONVERT_SCRIPT="./convert_fast.sh"

# Remove the destination directory if it exists
rm -rf "$dest_dir"

# Ensure the destination directory exists
mkdir -p "$dest_dir"

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

# Get list of all files using a macOS-compatible approach
echo "Finding files to process..."
all_files=()
while IFS= read -r file; do
    all_files+=("$file")
done < <(find "$source_dir" -name "*.doc*")

total=${#all_files[@]}
echo "Found $total files to process"

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
    local count=$(cat "$job_count_file")
    echo $((count - 1)) > "$job_count_file"
}

# Track number of completed files
completed=0

# Function to update progress display
update_progress() {
    # Count successful and failed conversions
    local success_count=$(ls "$STATUS_DIR"/*.success 2>/dev/null | wc -l | tr -d ' ')
    local error_count=$(ls "$STATUS_DIR"/*.error 2>/dev/null | wc -l | tr -d ' ')
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
    current_jobs=$(cat "$job_count_file")
    while [ "$current_jobs" -ge $MAX_JOBS ]; do
        update_progress
        sleep 0.1
        current_jobs=$(cat "$job_count_file")
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

while [ "$(cat "$job_count_file")" -gt 0 ] && [ $timeout_counter -lt $max_timeout ]; do
    update_progress
    sleep 1
    timeout_counter=$((timeout_counter + 1))
done

# Handle timeout
if [ $timeout_counter -ge $max_timeout ]; then
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

echo "All done!"
exit 0