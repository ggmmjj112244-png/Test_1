#!/bin/bash
unset GITHUB_TOKEN
TOKEN="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"
echo $TOKEN | gh auth login --with-token
gh auth setup-git
git push origin main
