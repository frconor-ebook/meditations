#!/bin/bash

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown"

# Ensure the destination directory exists
mkdir -p "$dest_dir"

# Count total .doc/.docx files in the source directory
total=$(find "$source_dir" -name "*.doc*" | wc -l)
echo "Found $total files to process."

# Check if GNU Parallel is installed
if ! command -v parallel &> /dev/null; then
    echo "GNU Parallel is not installed. Please install it first."
    echo "On macOS: brew install parallel"
    echo "On Ubuntu/Debian: apt-get install parallel"
    exit 1
fi

# Run parallel citation once to suppress the notice
parallel --citation >/dev/null 2>&1 || true

# Create a counter file for progress tracking
counter_file=$(mktemp)
echo "0" > "$counter_file"

# Define a conversion function that uses a unique temporary directory for each file
convert_file() {
    local doc_file="$1"
    local basename=$(basename "$doc_file" | sed 's/\.doc[x]*$//')
    local markdown_file="$dest_dir/$basename.md"

    # Create a unique temporary directory for this process
    local temp_dir=$(mktemp -d)
    cd "$temp_dir" || exit 1

    # Update and display progress counter
    local count=$(cat "$counter_file")
    count=$((count + 1))
    echo "$count" > "$counter_file"
    printf "[%d/%d] Processing: %s\n" "$count" "$total" "$doc_file"

    # Convert the file using convert.sh with full paths
    "$convert_script" "$doc_file" > "$markdown_file"

    local status=$?

    # Check if the conversion was successful
    if [ $status -eq 0 ]; then
        printf "[%d/%d] ✅ Successfully converted: %s\n" "$count" "$total" "$(basename "$doc_file")"
    else
        printf "[%d/%d] ❌ Error converting: %s\n" "$count" "$total" "$(basename "$doc_file")"
    fi

    # Clean up the temporary directory
    cd "$OLDPWD" || exit 1
    rm -rf "$temp_dir"

    return $status
}

# Get the absolute path to convert.sh
convert_script=$(realpath ./convert.sh)
if [ ! -x "$convert_script" ]; then
    echo "Error: convert.sh script not found or not executable"
    exit 1
fi

# Export the variables and function so parallel can use them
export -f convert_file
export dest_dir
export convert_script
export counter_file
export total

# Set the number of parallel jobs (cores)
# Using slightly fewer processes can help with stability
num_cores=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)
num_jobs=$((num_cores - 1))
echo "Using $num_jobs parallel processes"

# Create a temp file to collect results
results_file=$(mktemp)

# Run the conversions in parallel with output control
# Using --line-buffer to ensure output appears immediately
find "$source_dir" -name "*.doc*" -print0 |
    parallel --line-buffer --jobs "$num_jobs" --null convert_file 2>&1 | tee "$results_file"

# Count successes and failures
successful=$(grep -c "✅ Successfully converted" "$results_file")
failed=$(grep -c "❌ Error converting" "$results_file")

echo ""
echo "Conversion complete!"
echo "Total files: $total"
echo "Successfully converted: $successful files"
echo "Failed conversions: $failed files"

# Cleanup
rm -f "$counter_file" "$results_file"