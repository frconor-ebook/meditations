#!/bin/bash

# Check if input file is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_docx_file>"
    exit 1
fi

# Input file from command-line argument
input_docx="$1"

# Check if the file exists
if [ ! -f "$input_docx" ]; then
    echo "Error: File '$input_docx' not found!"
    exit 1
fi

# Temporary file for LibreOffice output
temp_file=$(mktemp)

# Extract title with LibreOffice, fully suppress verbose output
/Applications/LibreOffice.app/Contents/MacOS/soffice --convert-to "txt:Text (encoded):UTF8" "$input_docx" --headless > /dev/null 2>&1

# Locate the generated text file (LibreOffice saves it in the same directory as the input)
temp_file_name=$(basename "$input_docx" .docx).txt
mv "$temp_file_name" "$temp_file"

# Extract the first line (title) and clean up special characters using sed
title=$(head -n 1 "$temp_file" | sed 's/[^[:print:]]//g')

# Check if title extraction succeeded
if [ -z "$title" ]; then
    rm -f "$temp_file"
    echo "Error: Failed to extract title from '$input_docx'."
    exit 1
fi

# Convert body with Pandoc (directly in memory)
body=$(pandoc -t markdown "$input_docx" 2>/dev/null)

# Check if Pandoc succeeded
if [ -z "$body" ]; then
    rm -f "$temp_file"
    echo "Error: Failed to convert body from '$input_docx' using Pandoc."
    exit 1
fi

# Clean up the temporary file
rm -f "$temp_file"

# Combine title and body, output to STDOUT
{
    echo "# $title"
    echo
    echo "$body"
} | sed '/^convert .* as a Writer document/d'