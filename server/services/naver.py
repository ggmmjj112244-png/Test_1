import os
import requests
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

class NaverService:
    def __init__(self):
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET

    def search_news(self, query, display=10):
        """네이버 뉴스 검색 결과를 가져옵니다."""
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {
            "query": query,
            "display": display,
            "sort": "sim"
        }
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json().get('items', [])
        return []

    def search_reports(self, corp_name):
        """기업 리포트 관련 검색 결과를 가져옵니다."""
        # '기업명 리포트' 키워드로 뉴스 검색 결과 활용
        query = f"{corp_name} 리포트"
        return self.search_news(query, display=5)

naver_service = NaverService()
