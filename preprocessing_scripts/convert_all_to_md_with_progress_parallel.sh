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

# Create a temporary directory for logs
tmpdir=$(mktemp -d)
success_log="$tmpdir/success.log"
error_log="$tmpdir/error.log"
touch "$success_log" "$error_log"

# Function to convert a single file
convert_file() {
    local doc_file="$1"
    local markdown_file="$dest_dir/$(basename "$doc_file" | sed 's/\.doc[x]*$/.md/')"

    # Convert the file
    if "$CONVERT_SCRIPT" "$doc_file" > "$markdown_file" 2>/dev/null; then
        echo "✓ $(basename "$doc_file")" >> "$success_log"
    else
        echo "✗ $(basename "$doc_file")" >> "$error_log"
    fi
}

# Count total .doc/.docx files in the source directory
total=$(find "$source_dir" -name "*.doc*" | wc -l)
echo "Found $total files to process"

# Process files in parallel
find "$source_dir" -name "*.doc*" | while read -r doc_file; do
    # Wait if we've reached the maximum number of background jobs
    while [ $(jobs -p | wc -l) -ge $MAX_JOBS ]; do
        sleep 0.1
    done

    # Start the conversion in the background
    convert_file "$doc_file" &

    # Show live progress based on completed files
    completed=$(( $(wc -l < "$success_log") + $(wc -l < "$error_log") ))
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

# Clean up temporary files
rm -rf "$tmpdir"

if [ $errors -gt 0 ]; then
    echo "Some files failed to convert. Check the error messages above."
    exit 1
fi

exit 0