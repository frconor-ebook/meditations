# Deployment Workflow for the Online Meditations
[![Jekyll](https://img.shields.io/badge/built%20with-Jekyll-red.svg)](https://jekyllrb.com/)
[![Markdown](https://img.shields.io/badge/markdown-%23000000.svg?logo=markdown)](https://www.markdownguide.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This document outlines the workflow for processing, building, and deploying the Meditations online. This process is typically performed monthly to incorporate edits from Meg Francisco.

This repository is hosted remotely here: `https://github.com/frconor-ebook/meditations`



## Quick Workflow Steps

This section provides a streamlined alternative to the *Detailed Workflow* (below), consolidating multiple processing steps into an automated pipeline.

**Step 1: Run the Preprocessing Pipeline**

Run the wrapper script to automatically download files from Dropbox, convert DocX to Markdown, standardize filenames, and process Markdown files:

```bash
cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/
./preprocess_wrapper.sh
```

The script will:
- Automatically download the latest files from the designated Dropbox shared folder
- Extract the files, replacing any existing content in the target directory
- Remove the downloaded zip file and any macOS-specific metadata folders
- Convert all DocX files to Markdown format
- Standardize filenames according to the project conventions
- Process the Markdown files to prepare them for the website

**Step 2: Build the Jekyll Site**

```bash
bundle exec jekyll clean
bundle exec jekyll build
```

**Step 3: Test the Site Locally**

```bash
bundle exec jekyll serve
```

Open your web browser and navigate to: `http://127.0.0.1:4000/meditations/`

Verify that the site is functioning correctly and that all modifications have been applied. Once testing is complete, stop the local server by pressing `Ctrl+C` in the terminal.

**Step 4: Deploy to GitHub Pages**

```bash
git add .
git commit -m "Update with latest edits" # Use a descriptive commit message
git push origin main
```

The updated site will be automatically deployed to GitHub Pages and accessible at: `https://frconor-ebook.github.io/meditations/`

## Additional Options

The `preprocess_wrapper.sh` script supports several options:

```
Options:
  -v, --verbose         Enable verbose output
  -s, --skip-step STEP  Skip specific step (download|convert|standardize|process)
  -l, --log FILE        Write output to log file
  -h, --help            Display help message
```

For example, if you've already downloaded the files and only want to run the processing steps:

```bash
./preprocess_wrapper.sh --skip-step download
```

## Detailed Workflow Steps

**1. Download and Prepare Input Files**

1. Download the latest proofread Word DocX files from the designated Dropbox location.
2. Place these downloaded files into the following directory:
    `/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/`

**2. Convert DocX to Markdown**

1. Navigate to the preprocessing scripts directory:
    ```bash
    cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/preprocessing_scripts/
    ```
2. Execute the conversion script. This process may take approximately 30 minutes, as it reprocesses all DocX files to ensure all edits are captured.
    ```bash
    ./convert_all_to_md.sh
    ```
    This script generates Markdown files in:
    `/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown/`

**3. Standardize Filenames**

1. Ensure you are still in the preprocessing scripts directory:
    ```bash
    cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/preprocessing_scripts/
    ```
2. Run the filename standardization script:
    ```bash
    python standardize_filename.py
    ```
    This script creates standardized Markdown files in:
    `/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_std_markdown/`

**4. Process Markdown Files**

1. Navigate to the main `meditations` directory:
    ```bash
    cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations
    ```
2. Execute the Markdown processing script:
    ```bash
    python process_markdown.py
    ```

**5. Build the Jekyll Site**

1. Make sure you are in the `meditations` directory:
    ```bash
    cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations
    ```
2. Build the static site using Jekyll:
    ```bash
    bundle exec jekyll build
    ```

**6. Test the Site Locally**

1. Serve the site locally for testing:
    ```bash
    bundle exec jekyll serve
    ```
2. Open your web browser and navigate to:
    `http://127.0.0.1:4000/meditations/`
3. Verify that the site is functioning correctly and that all modifications have been applied.
4. Once testing is complete, stop the local server by pressing `Ctrl+C` in the terminal.

**7. Deploy to GitHub Pages**

1. Commit your changes to the Git repository:
    ```bash
    cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations
    git add .
    git commit -m "Update with latest edits" # Use a descriptive commit message
    git push origin main
    ```
2. The updated site will be automatically deployed to GitHub Pages and accessible at:
    `https://frconor-ebook.github.io/meditations/`


Note that Step 2 to 4 can be executed with:

```
cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/
./preprocess_wrapper.sh
```

### Notes

*   This workflow assumes the directory structure mentioned in the original text. Adjust the paths accordingly if your directory structure is different.
*   The `convert_all_to_md.sh` script is designed to be thorough and thus processes all DocX files each time. This ensures that all edits are consistently applied.
*   Ensure to regularly update the dependencies using Bundler:
    ```bash
    bundle update
    ```

### Troubleshooting

*   If you encounter issues with Jekyll, try running `bundle add webrick` and then `bundle install` again.
*   If you face any problem during any of the steps, please check the error message and make sure that you have followed the instruction correctly.
*   If the problem persists, you can check the issue in this GitHub repository page or email the maintainer.


## URL Shortening Scripts

This process uses three Python scripts for URL shortening: `create_long_urls.py`, `shorten_urls.py`, and `process_and_shorten.py`.

* **`create_long_urls.py`**: This script processes a JSON file containing meditation entries, extracts the slugs, and generates a new JSON file (`long_urls.json`) containing the corresponding long URLs.
* **`shorten_urls.py`**: This script provides the core functionality for creating custom shortened URLs. It leverages the TinyURL API for shortening and the Groq API for generating concise, human-readable aliases based on the content of the URL.
* **`process_and_shorten.py`**: This script orchestrates the entire URL shortening process. It first calls the `create_long_urls` function (from `create_long_urls.py`) to generate `long_urls.json` from a meditations input JSON file. Then, it reads the list of long URLs from `long_urls.json`, calls the `create_custom_short_url` function from `shorten_urls.py` to shorten each URL, and finally saves the results (each long URL and its corresponding shortened URL) to a CSV file (`shortened_urls.csv`). It also skips URLs that have already been processed to avoid duplicates.

**Interrelation:**
- `process_and_shorten.py` imports and uses the `create_long_urls` function defined in `create_long_urls.py` to generate the list of long URLs.
- It also imports and uses the `create_custom_short_url` function defined in `shorten_urls.py` to perform the actual URL shortening.

**Usage:**
For the complete processing, simply run `process_and_shorten.py`. This script will generate `long_urls.json` and then process and shorten the URLs accordingly.


