#!/bin/bash

# Complete parallel conversion wrapper for convert_fast.sh
# Ensures ALL files are processed with robust progress tracking

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown"

# Path to the conversion script
CONVERT_SCRIPT="./convert_fast.sh"

# Ensure the destination directory exists
mkdir -p "$dest_dir"

# Determine number of CPU cores for optimal parallelism
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

# Create a list of all files to process
file_list=$(mktemp)
find "$source_dir" -name "*.doc*" > "$file_list"
total=$(wc -l < "$file_list")
echo "Found $total files to process"

# Create tracking files
processed_marker=$(mktemp)
success_list=$(mktemp)
failed_list=$(mktemp)

# Process a single file
process_file() {
    local input_file="$1"
    local base_name=$(basename "$input_file" | sed 's/\.doc[x]*$/.md/')
    local output_file="$dest_dir/$base_name"

    # Perform the conversion
    if "$CONVERT_SCRIPT" "$input_file" > "$output_file" 2>/dev/null; then
        # Report success
        echo "$input_file" >> "$success_list"
    else
        # Report failure
        echo "$input_file" >> "$failed_list"
    fi

    # Mark as processed (for progress tracking)
    echo "x" >> "$processed_marker"
}

# Export function and variables for subshell use
export -f process_file
export CONVERT_SCRIPT
export dest_dir
export success_list
export failed_list
export processed_marker

# Use GNU Parallel if available (much more reliable than xargs)
if command -v parallel &>/dev/null; then
    echo "Using GNU Parallel for processing"
    cat "$file_list" | parallel -j $MAX_JOBS process_file
else
    # Alternative approach - process files in batches
    echo "Using batch processing"

    # Split the file list into smaller chunks
    split -l 10 "$file_list" "$file_list.chunk."
    chunks=$(ls "$file_list.chunk."*)

    for chunk in $chunks; do
        # Process up to MAX_JOBS files in parallel from this chunk
        cat "$chunk" | while read -r file; do
            # Wait if we already have MAX_JOBS running
            while [ "$(jobs -r | wc -l)" -ge "$MAX_JOBS" ]; do
                sleep 0.5
            done

            # Process this file in the background
            process_file "$file" &

            # Show progress
            processed=$(wc -l < "$processed_marker" 2>/dev/null || echo 0)
            percent=$((processed * 100 / total))
            printf "\rProgress: [%-50s] %d%% (%d/%d)" \
                "$(printf '#%.0s' $(seq 1 $(( percent / 2 ))))" \
                "$percent" "$processed" "$total"
        done

        # Wait for this batch to complete before starting the next
        wait
    done

    # Clean up chunk files
    rm -f "$file_list.chunk."*
fi

# Wait for all background processes to complete
wait

# Final statistics
success_count=$(wc -l < "$success_list" 2>/dev/null || echo 0)
failed_count=$(wc -l < "$failed_list" 2>/dev/null || echo 0)
processed_count=$((success_count + failed_count))

echo
echo "Conversion complete!"
echo "Successfully converted: $success_count files"
echo "Failed conversions: $failed_count files"
echo "Total processed: $processed_count of $total files"

# Verify all files were processed
if [ "$processed_count" -ne "$total" ]; then
    echo "WARNING: Not all files were processed!"
    echo "Missing: $((total - processed_count)) files"

    # Find which files were missed
    echo "Identifying missed files..."
    tmp_all=$(mktemp)
    tmp_processed=$(mktemp)

    # Create lists for comparison
    cat "$file_list" > "$tmp_all"
    cat "$success_list" "$failed_list" > "$tmp_processed"

    # Find files in all list but not in processed list
    echo "Missed files:"
    grep -v -f "$tmp_processed" "$tmp_all" || echo "Could not determine missed files"

    # Clean up
    rm -f "$tmp_all" "$tmp_processed"
fi

# List failed files if any
if [ "$failed_count" -gt 0 ]; then
    echo "Failed files:"
    cat "$failed_list"
fi

# Clean up
rm -f "$file_list" "$processed_marker" "$success_list" "$failed_list"

exit 0