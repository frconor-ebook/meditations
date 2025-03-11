# Deployment Workflow for the Online Meditations
[![Jekyll](https://img.shields.io/badge/built%20with-Jekyll-red.svg)](https://jekyllrb.com/)
[![Markdown](https://img.shields.io/badge/markdown-%23000000.svg?logo=markdown)](https://www.markdownguide.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This document outlines the workflow for processing, building, and deploying the Meditations online. This process is typically performed monthly to incorporate edits from Meg Francisco.

This repository is hosted remotely here: `https://github.com/frconor-ebook/meditations`




## Quick Workflow

The complete workflow has been automated into a single script that handles everything from downloading files to deploying to GitHub Pages.

**Run the Full Pipeline Script**

```bash
cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/
./frcmed_full_pipeline.sh
```

This script will automatically:

1. **Preprocessing Phase**
   - Download the latest files from the designated Dropbox shared folder
   - **Note: You may occasionally need to authenticate by copying and pasting an authorization code when prompted. This happens when the Dropbox access token expires (typically every few days), which is a security feature of the Dropbox API.**
   - Extract the files, replacing any existing content in the target directory
   - Remove the downloaded zip file and any macOS-specific metadata folders
   - Convert all DocX files to Markdown format
   - Standardize filenames according to the project conventions
   - Process the Markdown files to prepare them for the website

2. **Build Phase**
   - Clean the Jekyll site
   - Build the Jekyll site

3. **Deployment Phase**
   - Commit all changes to git
   - Push to GitHub Pages

After deployment, the site will be accessible at: `https://frconor-ebook.github.io/meditations/`

## Testing Locally

If you want to test the site before deploying, you can use the following command after running the pipeline with the `--skip-step deploy` option:

```bash
bundle exec jekyll serve
```

Open your web browser and navigate to: `http://127.0.0.1:4000/meditations/`

Verify that the site is functioning correctly and that all modifications have been applied. Once testing is complete, stop the local server by pressing `Ctrl+C` in the terminal.

## Additional Options

The `frcmed_full_pipeline.sh` script supports several options:

```
Options:
  -v, --verbose           Enable verbose output
  -s, --skip-step STEPS   Skip specific step(s) (comma-separated list)
                          Valid steps: download,convert,standardize,process,build,deploy
  -i, --include-step STEPS Only run specific step(s) (comma-separated list)
                          Valid steps: download,convert,standardize,process,build,deploy
  -l, --log FILE          Write output to log file
  -h, --help              Display help message
```

### Common Usage Examples

**Skip downloading and only process existing files:**
```bash
./frcmed_full_pipeline.sh --skip-step download
```

**Process content but skip deployment (for testing):**
```bash
./frcmed_full_pipeline.sh --skip-step deploy
```

**Skip both build and deploy steps at once:**
```bash
./frcmed_full_pipeline.sh --skip-step build,deploy
```

**Only run specific steps:**
```bash
# Only download and process files
./frcmed_full_pipeline.sh --include-step download,process

# Only build and deploy the site
./frcmed_full_pipeline.sh --include-step build,deploy

# Only download files
./frcmed_full_pipeline.sh --include-step download
```

**Generate detailed logs:**
```bash
./frcmed_full_pipeline.sh --verbose --log pipeline.log
```

## Workflow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Download   │────>│   Convert   │────>│ Standardize │────>│   Process   │
│  from       │     │   to        │     │  Filenames  │     │  Markdown   │
│  Dropbox    │     │  Markdown   │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐                         ┌─────────────┐
│   Deploy    │<────│    Build    │<────────────────────────│ Preprocessing│
│  to GitHub  │     │   Jekyll    │                         │  Complete   │
│    Pages    │     │    Site     │                         │             │
└─────────────┘     └─────────────┘                         └─────────────┘
```

## Step-by-Step Execution

You can run each step individually using the `--include-step` option:

1. **Download files from Dropbox**
   ```bash
   ./frcmed_full_pipeline.sh --include-step download
   ```

2. **Convert DocX to Markdown**
   ```bash
   ./frcmed_full_pipeline.sh --include-step convert
   ```

3. **Standardize filenames**
   ```bash
   ./frcmed_full_pipeline.sh --include-step standardize
   ```

4. **Process Markdown files**
   ```bash
   ./frcmed_full_pipeline.sh --include-step process
   ```

5. **Build Jekyll site**
   ```bash
   ./frcmed_full_pipeline.sh --include-step build
   ```

6. **Deploy to GitHub Pages**
   ```bash
   ./frcmed_full_pipeline.sh --include-step deploy
   ```

You can also combine steps as needed:
```bash
# Preprocess and build, but don't deploy
./frcmed_full_pipeline.sh --include-step download,convert,standardize,process,build
```

## Troubleshooting

If you encounter issues:

1. Run with `--verbose` flag to see detailed logs
2. Check the log file if you used the `--log` option
3. Ensure all dependencies are installed (Python 3, Jekyll, Ruby, Git)
4. Verify you have access permissions to the Dropbox folder
5. Ensure your Git credentials are configured correctly

## Notes

- The `--include-step` and `--skip-step` options cannot be used together
- Using the `--include-step` option will only run the specified steps
- Using the `--skip-step` option will run all steps except the specified ones


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


## Getting a Dropbox Refresh Token

To obtain a Dropbox refresh token for the automatic download process, follow these steps:

1. **Generate an Authorization URL**
   ```
   https://www.dropbox.com/oauth2/authorize?client_id=YOUR_APP_KEY&response_type=code&token_access_type=offline
   ```
   Replace `YOUR_APP_KEY` with your Dropbox App Key.

2. **Authorize the Application**
   - Open the URL in a web browser
   - Log in to Dropbox if prompted
   - Click "Allow" to authorize the application

3. **Capture the Authorization Code**
   - After authorization, Dropbox will display an authorization code on the screen
   - This code is temporary and will expire in a few minutes

4. **Exchange for a Refresh Token**
   Run the following curl command:
   ```bash
   curl -X POST https://api.dropboxapi.com/oauth2/token \
     -d code=THE_AUTHORIZATION_CODE \
     -d grant_type=authorization_code \
     -d client_id=YOUR_APP_KEY \
     -d client_secret=YOUR_APP_SECRET
   ```
   Replace:
   - `THE_AUTHORIZATION_CODE` with the code from step 3
   - `YOUR_APP_KEY` with your Dropbox App Key
   - `YOUR_APP_SECRET` with your Dropbox App Secret

5. **Extract the Refresh Token**
   - The response will be a JSON object containing both `access_token` and `refresh_token`
   - Copy the value of `refresh_token` from the response

6. **Update Your .env File**
   Add or update the following line in your `.env` file:
   ```
   DROPBOX_REFRESH_TOKEN=your_refresh_token
   ```

The refresh token is long-lived and will be used automatically by the script to obtain new access tokens when they expire. You typically only need to perform this process once unless you revoke the token or reset your app's permissions.