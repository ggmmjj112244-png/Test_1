#!/bin/bash
unset GITHUB_TOKEN
TOKEN="YOUR_GITHUB_TOKEN_HERE"
echo $TOKEN | gh auth login --with-token
gh auth setup-git
git push origin main
