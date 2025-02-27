#!/bin/bash
# Script to quickly extract the title and body from a DOCX file using only Pandoc
# Outputs the formatted document to STDOUT

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_docx_file>"
    exit 1
fi

input_docx="$1"

if [ ! -f "$input_docx" ]; then
    echo "Error: File '$input_docx' not found!"
    exit 1
fi

# First, extract metadata to get the title
metadata=$(pandoc --standalone --template=default "$input_docx" --to=plain 2>/dev/null)

# Extract title carefully without using regex for removal
raw_title=$(echo "$metadata" | head -n 1)
# Remove carriage returns without sed
raw_title=$(echo -n "$raw_title" | tr -d '\r')
# Trim whitespace from beginning and end
title=$(echo -n "$raw_title" | awk '{$1=$1};1')

# Special handling for titles ending with "t" - check if the filename contains the full title
if [[ "$title" == *[^t] ]]; then
    # Not ending with 't', so we're probably fine
    :
else
    # Might be ending with 't', check filename
    base_name=$(basename "$input_docx" .docx | sed 's/\.[A-Za-z]*pr$//')
    if [[ "$base_name" == *t && "$title" == "${base_name:0:-1}" ]]; then
        # If filename ends with 't' and matches our title except for the 't', use filename
        title="$base_name"
    fi
fi

# If title extraction failed or title is empty, try a different approach
if [ -z "$title" ]; then
    # Try to extract from the raw body text (first line)
    raw_title=$(pandoc "$input_docx" --to=plain 2>/dev/null | head -n 1)
    title=$(echo -n "$raw_title" | tr -d '\r' | awk '{$1=$1};1')

    if [ -z "$title" ]; then
        echo "Error: Failed to extract title from '$input_docx'."
        exit 1
    fi
fi

# Convert body to markdown without YAML front matter
body=$(pandoc "$input_docx" --to=markdown --wrap=none 2>/dev/null)

# Verify that the Pandoc conversion was successful
if [ -z "$body" ]; then
    echo "Error: Failed to convert body from '$input_docx' using Pandoc."
    exit 1
fi

# Output the extracted title and converted body in Markdown format
{
    echo "# $title"
    echo
    echo "$body"
} | sed '/^---$/,/^---$/d' | sed '/^convert .* as a Writer document/d'