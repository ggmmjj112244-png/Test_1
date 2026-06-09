#!/bin/bash
unset GITHUB_TOKEN
echo "YOUR_GITHUB_TOKEN_HERE" | gh auth login --with-token
gh auth setup-git
git push origin main
