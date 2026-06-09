import os
import requests
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

import re

class NaverService:
    def __init__(self):
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET

    def _clean_html(self, text):
        """HTML 태그 제거"""
        if not text: return ""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)

    def search_news(self, query, display=15):
        """네이버 뉴스 검색 결과를 가져옵니다. 최신순(date)으로 정렬하여 신선도를 높임."""
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {
            "query": query,
            "display": display,
            "sort": "date"  # 'sim'(유사도) 대신 'date'(최신순) 사용
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                items = response.json().get('items', [])
                for item in items:
                    item['title'] = self._clean_html(item['title'])
                    item['description'] = self._clean_html(item['description'])
                return items
        except Exception as e:
            print(f"Naver News API Error: {e}")
        return []

    def search_reports(self, corp_name):
        """기업 분석 리포트 관련 뉴스 검색"""
        query = f"{corp_name} (분석 OR 리포트 OR 전망)"
        return self.search_news(query, display=5)

naver_service = NaverService()
