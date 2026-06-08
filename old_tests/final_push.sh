#!/bin/bash
TOKEN="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"
CONTENT=$(base64 -w 0 index.html)
GH_TOKEN="$TOKEN" gh api --method PUT /repos/ggmmjj112244-png/Test_1/contents/index.html \
  -f message="Initial commit: Add index.html for Chart Hero site" \
  -f content="$CONTENT"
