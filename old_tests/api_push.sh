#!/bin/bash
CONTENT=$(base64 -w 0 index.html)
gh api --method PUT /repos/ggmmjj112244-png/Test_1/contents/index.html \
  -f message="Initial commit: Add index.html for Chart Hero site" \
  -f content="$CONTENT"
