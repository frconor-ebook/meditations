# Fr. Conor Donnelly Meditations

This repository contains the source code for a website that displays a collection of meditations by Fr. Conor Donnelly. The website is built using Jekyll and hosted on GitHub Pages.

## Processing Markdown Files

1. **Place Markdown Files:** Put your proofread markdown files (e.g., from `../transcript_proofread_markdown`) into the `transcript_proofread_markdown_small` directory. Each markdown file should contain the content of a single meditation.

2. **Run the Script:**

    ```bash
    python process_markdown.py
    ```

    *   This script will:
        *   Convert each markdown file in `transcript_proofread_markdown_small` into a Jekyll post in the `_posts` directory.
        *   Generate a `meditations.json` file in the `_data` directory, which contains metadata for the search functionality.

## Building and Running the Site Locally

1. **Go to Related Directory:**

    ```bash
    cd /Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations
    ```


2. **Build the Site:**

    ```bash
    bundle exec jekyll build
    ```

    This command will generate the static website files in the `docs` directory.

3. **Start the Development Server:**

    ```bash
    bundle exec jekyll serve
    ```

    This will start a local development server. You can view your website by opening `http://127.0.0.1:4000/meditations/` in your browser.

## Deploying to GitHub Pages

1. **Commit and Push Changes:**

    ```bash
    git add .
    git commit -m "Add meditations and build site"
    git push origin main
    ```

2. **Configure GitHub Pages:**

    *   Go to your repository on GitHub and navigate to **Settings > Pages**.
    *   Under **Source**, choose the `main` branch and the `/docs` folder.
    *   Click **Save**.

3. **Wait for Deployment:**

    *   GitHub Pages will take a few minutes to build and deploy your site. You can monitor the progress in the **Actions** tab of your repository.

4. **View Your Website:**

    *   Once deployed, your website will be accessible at `https://frconor-ebook.github.io/meditations/`.

## Updating the Website

1. **Add or Modify Meditations:** Place new or updated markdown files in `transcript_proofread_markdown_small`.
2. **Run `process_markdown.py`:**
    ```bash
    python process_markdown.py
    ```
3. **Rebuild the Site:**
    ```bash
    bundle exec jekyll build
    ```
4. **Commit and Push:**
    ```bash
    git add .
    git commit -m "Update meditations"
    git push origin main
    ```

GitHub Pages will automatically rebuild and redeploy your site.

## Troubleshooting

*   **Search Not Working:**
    *   Make sure `meditations.json` is being generated correctly in `_data`.
    *   Verify that the `fetch` URL in `search.js` is correct (`/meditations/_data/meditations.json`).
    *   Use your browser's developer tools (Network tab) to check if `meditations.json` is being fetched successfully.
*   **Permissions Errors:**
    *   If you encounter permission errors, make sure your user account has write access to the `docs` directory and its contents. You might need to adjust ownership or permissions using `chown` or `chmod`.
*   **Jekyll Build Errors:**
    *   Carefully examine the error messages from Jekyll. They often provide clues about the problem (e.g., incorrect YAML front matter, missing files, etc.).
    *   Check your `_config.yml` for any errors.

## Notes

*   This `README.md` assumes you are using the recommended setup where `meditations.json` is generated in the root `_data` directory and then copied to `docs/_data` by Jekyll.
*   The `create_project.sh` script is not essential for the core functionality but can be used to initially set up the project structure.
*   Remember to replace placeholder values (like your GitHub username) with your actual information.

This detailed `README.md` should provide a clear and comprehensive guide for setting up, building, deploying, and maintaining your Fr. Conor Donnelly Meditations website. Let me know if you have any more questions.
