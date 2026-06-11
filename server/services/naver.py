import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

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

    def get_stock_info(self, stock_code):
        """네이버 증권 기업현황(기업개요/매출구성) 및 종목뉴스를 수집합니다. (정성적 정보 위주)"""
        if not stock_code:
            return None

        blocks = []

        overview_block = self._get_company_overview_from_naver(stock_code)
        if overview_block:
            blocks.append(overview_block)

        news_block = self._get_stock_news(stock_code)
        if news_block:
            blocks.append(news_block)

        if not blocks:
            return None

        return "\n\n".join(blocks)

    def _get_company_overview_from_naver(self, stock_code):
        """네이버 증권 '기업현황' 탭(FnGuide)에서 기업개요와 매출구성을 가져옵니다."""
        headers = {"User-Agent": USER_AGENT}
        parts = []

        # 1) 기업개요 설명 텍스트 (c1010001)
        try:
            url = f"https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={stock_code}"
            response = requests.get(url, headers=headers, timeout=8)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            summary_el = soup.select_one('.cmp_comment')
            if summary_el:
                summary_text = summary_el.get_text(separator=' ', strip=True)
                if len(summary_text) > 1200:
                    summary_text = summary_text[:1200] + "..."
                parts.append(f"[기업개요]\n{summary_text}")
        except Exception as e:
            print(f"--- Naver Stock Overview Parse Error: {e}")

        # 2) 주요제품 매출구성 (c1020001, 차트 데이터)
        try:
            url = f"https://navercomp.wisereport.co.kr/v2/company/c1020001.aspx?cmp_cd={stock_code}"
            response = requests.get(url, headers=headers, timeout=8)
            response.encoding = response.apparent_encoding

            m = re.search(r'chartData1\s*=\s*(\[\[.*?\]\]);', response.text, re.DOTALL)
            if m:
                items = re.findall(r'\["([^"]+)"\s*,\s*([\d.]+)\]', m.group(1))
                if items:
                    lines = [f"- {name}: {ratio}%" for name, ratio in items]
                    parts.append("[주요 제품/사업부문별 매출 비중]\n" + "\n".join(lines))
        except Exception as e:
            print(f"--- Naver Stock Revenue Composition Error: {e}")

        if not parts:
            return None

        return "## 네이버 증권 - 기업현황\n" + "\n\n".join(parts)

    def _get_stock_news(self, stock_code, limit=8):
        """네이버 증권 종목뉴스 탭에서 최근 뉴스 제목/날짜 목록을 가져옵니다."""
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1"
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Referer": f"https://finance.naver.com/item/main.naver?code={stock_code}"
            }
            response = requests.get(url, headers=headers, timeout=8)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            items = []
            for tr in soup.select('table.type5 tr'):
                tds = tr.find_all('td', recursive=False)
                title_td = next((td for td in tds if 'title' in (td.get('class') or [])), None)
                date_td = next((td for td in tds if 'date' in (td.get('class') or [])), None)
                if not title_td or not date_td:
                    continue
                title = title_td.get_text(strip=True)
                date = date_td.get_text(strip=True)
                if not title:
                    continue
                items.append(f"- [{date}] {title}")
                if len(items) >= limit:
                    break

            if not items:
                return None

            return "## 네이버 증권 - 종목뉴스\n" + "\n".join(items)
        except Exception as e:
            print(f"--- Naver Stock News Error: {e}")
            return None

naver_service = NaverService()
