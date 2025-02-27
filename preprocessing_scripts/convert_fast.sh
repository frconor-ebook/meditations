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
title=$(echo "$metadata" | head -n 1 | sed 's/[^[:print:]]//g' | sed 's/^[ \t]*//;s/[ \t]*$//')

# If title extraction failed or title is empty, try a different approach
if [ -z "$title" ]; then
    # Try to extract from the raw body text (first line)
    title=$(pandoc "$input_docx" --to=plain 2>/dev/null | head -n 1 | sed 's/[^[:print:]]//g' | sed 's/^[ \t]*//;s/[ \t]*$//')

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