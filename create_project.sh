#!/bin/bash

# Create directories
mkdir -p _posts docs/assets/css docs/assets/js docs/homilies _data _includes _layouts transcript_proofread_markdown_small

# Create placeholder files (you'll fill these in later)
touch docs/assets/css/style.css
touch docs/assets/js/search.js
touch _data/meditations.json
touch _includes/header.html
touch _includes/footer.html
touch _includes/search.html
touch _layouts/default.html
touch _layouts/homily.html
touch index.md

# Create example markdown files (replace with your actual files later)
touch transcript_proofread_markdown_small/A-Christian-Outlook-on-Death.OLVpr.md
touch transcript_proofread_markdown_small/Abandonment-2022.OLVpr.md

echo "Project structure created!"