#!/bin/bash

# Parallel conversion wrapper for convert_fast.sh
# Processes multiple files simultaneously for faster conversion

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown"

# Path to the conversion script
CONVERT_SCRIPT="./convert_fast.sh"

# Ensure the destination directory exists
mkdir -p "$dest_dir"

# Determine number of CPU cores for optimal parallelism
# Use 75% of available cores to avoid overwhelming the system
if command -v nproc &>/dev/null; then
    NUM_CORES=$(nproc)
elif [ -f /proc/cpuinfo ]; then
    NUM_CORES=$(grep -c ^processor /proc/cpuinfo)
else
    # On macOS
    NUM_CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
fi
MAX_JOBS=$(( NUM_CORES * 3 / 4 ))
[ $MAX_JOBS -lt 1 ] && MAX_JOBS=1

echo "Using $MAX_JOBS parallel processes"

# Create a permanent directory for logs in the current directory
log_dir="./conversion_logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$log_dir"
success_log="$log_dir/success.log"
error_log="$log_dir/error.log"
progress_log="$log_dir/progress.log"
touch "$success_log" "$error_log" "$progress_log"

echo "Logs will be stored in: $log_dir"

# Initialize the progress log
echo "0" > "$progress_log"

# Function to convert a single file
convert_file() {
    local doc_file="$1"
    local markdown_file="$dest_dir/$(basename "$doc_file" | sed 's/\.doc[x]*$/.md/')"

    # Convert the file
    if "$CONVERT_SCRIPT" "$doc_file" > "$markdown_file" 2>/dev/null; then
        # Use atomic file operations for thread safety
        echo "✓ $(basename "$doc_file")" >> "${success_log}.tmp.$$"
        mv "${success_log}.tmp.$$" "${success_log}.$$"
        cat "${success_log}.$$" >> "$success_log"
        rm "${success_log}.$$"
    else
        echo "✗ $(basename "$doc_file")" >> "${error_log}.tmp.$$"
        mv "${error_log}.tmp.$$" "${error_log}.$$"
        cat "${error_log}.$$" >> "$error_log"
        rm "${error_log}.$$"
    fi

    # Increment progress counter atomically
    lock_file="${progress_log}.lock"
    while ! mkdir "$lock_file" 2>/dev/null; do
        sleep 0.1
    done
    current=$(cat "$progress_log")
    echo $((current + 1)) > "$progress_log"
    rmdir "$lock_file"
}

# Count total .doc/.docx files in the source directory
mapfile -t all_files < <(find "$source_dir" -name "*.doc*")
total=${#all_files[@]}
echo "Found $total files to process"

# Process files in parallel
for doc_file in "${all_files[@]}"; do
    # Wait if we've reached the maximum number of background jobs
    while [ $(jobs -p | wc -l) -ge $MAX_JOBS ]; do
        sleep 0.1
    done

    # Start the conversion in the background
    convert_file "$doc_file" &

    # Show live progress based on completed files
    completed=$(cat "$progress_log")
    percent=$(( completed * 100 / total ))
    printf "\rProgress: [%-50s] %d%% (%d/%d)" \
        "$(printf '#%.0s' $(seq 1 $(( percent / 2 ))))" \
        "$percent" "$completed" "$total"
done

# Wait for all background jobs to complete
wait

# Final statistics
completed=$(wc -l < "$success_log")
errors=$(wc -l < "$error_log")

echo
echo "Conversion complete!"
echo "Successfully converted: $completed files"
echo "Failed conversions: $errors files"

# List any files that weren't processed
if [ $((completed + errors)) -lt $total ]; then
    echo "Warning: $(($total - completed - errors)) files were not processed:"
    for doc_file in "${all_files[@]}"; do
        filename=$(basename "$doc_file")
        if ! grep -q "$filename" "$success_log" && ! grep -q "$filename" "$error_log"; then
            echo "  - $filename"
        fi
    done
fi

echo "Detailed logs available in: $log_dir"

exit 0