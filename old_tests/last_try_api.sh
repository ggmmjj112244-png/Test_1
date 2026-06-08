#!/bin/bash
TOKEN="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"
CONTENT=$(base64 -w 0 index.html)
GH_TOKEN="$TOKEN" gh api --method PUT /repos/ggmmjj112244-png/Test_1/contents/index.html \
  -f message="Initial commit" \
  -f content="$CONTENT"
