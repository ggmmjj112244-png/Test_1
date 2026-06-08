#!/bin/bash
TOKEN="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"
CONTENT=$(base64 -w 0 index.html)
GH_TOKEN="$TOKEN" gh api --method PUT /repos/ggmmjj112244-png/Test_1/contents/index.html \
  -f message="Initial commit" \
  -f content="$CONTENT"
