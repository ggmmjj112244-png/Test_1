import os
import requests
from dotenv import load_dotenv

load_dotenv()

# 따옴표와 공백을 모두 제거하는 함수
def clean_env_var(value):
    if not value: return ""
    return value.strip("'\" ")

NAVER_CLIENT_ID = clean_env_var(os.getenv("NAVER_CLIENT_ID", ""))
NAVER_CLIENT_SECRET = clean_env_var(os.getenv("NAVER_CLIENT_SECRET", ""))

import re

class NaverService:
    def __init__(self):
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
        # 보안을 위해 앞 3글자만 로그에 출력하여 사용자 확인 지원
        id_preview = (self.client_id[:3] + "***") if self.client_id else "None"
        secret_preview = (self.client_secret[:3] + "***") if self.client_secret else "None"
        print(f"--- Naver ID Loaded: {id_preview} (Length: {len(self.client_id)})")
        print(f"--- Naver Secret Loaded: {secret_preview} (Length: {len(self.client_secret)})")

    def _clean_html(self, text):
        """HTML 태그 제거"""
        if not text: return ""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)

    def _search_naver(self, query, category="news", display=10):
        """네이버 검색 API 범용 호출 함수"""
        url = f"https://openapi.naver.com/v1/search/{category}.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {
            "query": query,
            "display": display,
            "sort": "sim"
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                items = response.json().get('items', [])
                for item in items:
                    item['title'] = self._clean_html(item['title'])
                    item['description'] = self._clean_html(item['description'])
                return items
        except Exception as e:
            print(f"Naver {category} API Error: {e}")
        return []

    def search_news(self, query, display=10):
        """뉴스 검색"""
        return self._search_naver(query, "news", display)

    def search_blog(self, query, display=5):
        """블로그 검색"""
        return self._search_naver(query, "blog", display)

    def search_cafe(self, query, display=5):
        """카페 검색"""
        return self._search_naver(query, "cafe", display)

    def search_reports(self, corp_name):
        """기업 분석 리포트 관련 뉴스 검색"""
        query = f"{corp_name} (분석 OR 리포트 OR 전망)"
        return self.search_news(query, display=5)

naver_service = NaverService()
