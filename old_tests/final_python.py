import base64
import requests

token = "YOUR_GITHUB_TOKEN_HERE"
with open('index.html', 'rb') as f:
    content = base64.b64encode(f.read()).decode()

url = "https://api.github.com/repos/ggmmjj112244-png/Test_1/contents/index.html"
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
data = {"message": "Initial commit", "content": content}
r = requests.put(url, headers=headers, json=data)
print(f"Status Code: {r.status_code}")
print(f"Response: {r.text}")
