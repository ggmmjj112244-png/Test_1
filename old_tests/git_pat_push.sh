#!/bin/bash
TOKEN="YOUR_GITHUB_TOKEN_HERE"
git -c credential.helper= push "https://x-access-token:$TOKEN@github.com/ggmmjj112244-png/Test_1.git" main
