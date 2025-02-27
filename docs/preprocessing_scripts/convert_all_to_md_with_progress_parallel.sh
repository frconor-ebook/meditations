#!/bin/bash

# macOS-compatible parallel conversion wrapper for convert_fast.sh with improved termination
# Processes multiple files simultaneously for faster conversion

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown"

# Path to the conversion script
CONVERT_SCRIPT="./convert_fast.sh"

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

# Use file-based tracking
success_log="$LOG_DIR/success.log"
error_log="$LOG_DIR/error.log"
pid_file="$LOG_DIR/pids.txt"

# Clear previous logs
> "$success_log"
> "$error_log"
> "$pid_file"

# Get list of all files
echo "Finding files to process..."
mapfile -t all_files < <(find "$source_dir" -name "*.doc*")
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

    # Signal completion by removing the PID from the file
    local current_pid=$$
    grep -v "^$current_pid$" "$pid_file" > "$pid_file.tmp" 2>/dev/null
    mv "$pid_file.tmp" "$pid_file" 2>/dev/null

    exit 0
}

# Track number of completed files
completed=0
active_jobs=0

# Function to update progress display
update_progress() {
    # Count successful and failed conversions
    local success_count=$(find "$STATUS_DIR" -name "*.success" 2>/dev/null | wc -l | tr -d ' ')
    local error_count=$(find "$STATUS_DIR" -name "*.error" 2>/dev/null | wc -l | tr -d ' ')
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
            find "$STATUS_DIR" -name "*.success" -exec cat {} \; > "$success_log" 2>/dev/null
        fi
        if [ $error_count -gt 0 ]; then
            find "$STATUS_DIR" -name "*.error" -exec cat {} \; > "$error_log" 2>/dev/null
        fi
    fi
}

# Process files in parallel with a better tracking mechanism
for i in "${!all_files[@]}"; do
    # Limit number of parallel jobs
    while [ $(pgrep -P $$ | wc -l) -ge $MAX_JOBS ]; do
        update_progress
        sleep 0.1
    done

    # Start conversion in background
    (
        convert_file "${all_files[$i]}" "$i"
    ) &

    # Record the background job's PID
    echo $! >> "$pid_file"

    # Update progress every 5 files
    if [ $((i % 5)) -eq 0 ] || [ $i -eq $((total - 1)) ]; then
        update_progress
    fi
done

# Monitor for completion with a timeout
echo
echo "Waiting for remaining jobs to complete..."
timeout_counter=0
max_timeout=30 # 30 seconds max wait

while [ -s "$pid_file" ] && [ $timeout_counter -lt $max_timeout ]; do
    update_progress
    sleep 1
    timeout_counter=$((timeout_counter + 1))
done

# If we hit the timeout, force cleanup
if [ $timeout_counter -ge $max_timeout ]; then
    echo "Timeout reached. Cleaning up..."
    # Read PIDs from file and kill them
    while read -r pid; do
        kill -9 $pid 2>/dev/null || true
    done < "$pid_file"
fi

# Final update of summary logs
find "$STATUS_DIR" -name "*.success" -exec cat {} \; > "$success_log" 2>/dev/null
find "$STATUS_DIR" -name "*.error" -exec cat {} \; > "$error_log" 2>/dev/null

# Final statistics
success_count=$(find "$STATUS_DIR" -name "*.success" 2>/dev/null | wc -l | tr -d ' ')
error_count=$(find "$STATUS_DIR" -name "*.error" 2>/dev/null | wc -l | tr -d ' ')

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
rm -f "$pid_file" "$pid_file.tmp"

echo "All done!"
exit 0