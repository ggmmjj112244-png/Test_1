import os
import re
import html
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")

class DartService:
    def __init__(self):
        self.api_key = DART_API_KEY
        self.corp_codes = {}  # {corp_name: corp_code}

    def update_corp_codes(self):
        """DART에서 고유번호 목록을 다운로드하여 메모리에 저장합니다."""
        key_preview = f"{self.api_key[:5]}***" if self.api_key else "None"
        print(f"--- Updating DART Corp Codes with Key: {key_preview}")
        url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={self.api_key}"
        try:
            response = requests.get(url, timeout=10)
            print(f"--- DART API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    xml_data = z.read('CORPCODE.xml')
                    tree = ET.fromstring(xml_data)
                    count = 0
                    for corp in tree.findall('list'):
                        name = corp.find('corp_name').text
                        code = corp.find('corp_code').text
                        self.corp_codes[name] = code
                        count += 1
                    print(f"--- Successfully loaded {count} corp codes.")
                return True
            else:
                print(f"--- Failed to download corp codes: {response.text}")
        except Exception as e:
            print(f"--- Error updating corp codes: {str(e)}")
        return False

    def get_corp_code(self, corp_name):
        """기업명으로 고유번호를 반환합니다."""
        if not self.corp_codes:
            print("--- Corp codes cache is empty. Updating...")
            self.update_corp_codes()
        
        # 정확히 일치하는 이름 찾기
        code = self.corp_codes.get(corp_name)
        if not code:
            # 부분 일치 검색 시도 (예: '삼성전자'가 '삼성전자(주)'로 되어 있을 수 있음)
            for name, c in self.corp_codes.items():
                if corp_name in name:
                    print(f"--- Found partial match: {name} -> {c}")
                    return c
        return code

    def get_latest_report(self, corp_code):
        """최신 사업보고서(11011)의 rcept_no를 가져옵니다."""
        url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={self.api_key}&corp_code={corp_code}&pblntf_ty=A&last_reprt_at=Y"
        response = requests.get(url).json()
        
        if response.get('status') == '000':
            # 정기공시 중 사업보고서(11011) 필터링 (보통 리스트 최상단)
            for item in response.get('list', []):
                if "사업보고서" in item.get('report_nm'):
                    return item.get('rcept_no')
        return None

    def get_company_info(self, corp_code):
        """기업 개요 정보를 가져옵니다 (기업개요 API)."""
        url = f"https://opendart.fss.or.kr/api/company.json?crtfc_key={self.api_key}&corp_code={corp_code}"
        try:
            response = requests.get(url).json()
            if response.get('status') == '000':
                return {
                    "corp_name": response.get('corp_name'),
                    "ceo_nm": response.get('ceo_nm'),
                    "induty_name": response.get('induty_name'), # 업종명 추가
                    "main_biz": response.get('main_biz'),
                    "hm_url": response.get('hm_url'),
                    "phn_no": response.get('phn_no')
                }
        except Exception as e:
            print(f"DART Company Info API Error: {e}")
        return None

    def get_company_overview(self, corp_code):
        """회사의 상세 개요 및 주요 사업을 상세히 가져옵니다."""
        info = self.get_company_info(corp_code)
        if not info:
            return "기업 정보를 수집할 수 없습니다."
        
        rcept_no = self.get_latest_report(corp_code)

        overview = f"### [기업 기본 정보: {info['corp_name']}]\n\n"
        overview += f"- **대표이사**: {info.get('ceo_nm', '정보 없음')}\n"
        overview += f"- **업종**: {info.get('induty_name', '정보 없음')}\n"
        overview += f"- **주요 사업**: {info.get('main_biz', '정보 없음')}\n"
        overview += f"- **홈페이지**: {info.get('hm_url', '정보 없음')}\n"

        if rcept_no:
            business_content = self.get_full_business_content(rcept_no)
            overview += f"\n### [최신 사업보고서 - 사업의 내용 (보고서 번호: {rcept_no})]\n\n"
            if business_content:
                overview += business_content
            else:
                overview += "사업보고서 원문에서 '사업의 내용' 섹션을 가져오지 못했습니다.\n"

        return overview

    def get_full_business_content(self, rcept_no):
        """DART 사업보고서 원문(document.xml)에서 'II. 사업의 내용' 섹션 텍스트를 추출합니다."""
        if not rcept_no:
            return None

        url = f"https://opendart.fss.or.kr/api/document.xml?crtfc_key={self.api_key}&rcept_no={rcept_no}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print(f"--- DART Document API HTTP Error: {response.status_code}")
                return None

            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                xml_name = next((n for n in z.namelist() if n.lower().endswith('.xml')), None)
                if not xml_name:
                    return None
                raw = z.read(xml_name)

            try:
                text = raw.decode('euc-kr')
            except UnicodeDecodeError:
                text = raw.decode('utf-8', errors='ignore')

            # 문서 내 섹션 제목들을 순서대로 찾아 '사업의 내용' 구간만 추출
            titles = list(re.finditer(r'<TITLE[^>]*>(.*?)</TITLE>', text, re.IGNORECASE | re.DOTALL))

            start, end = None, len(text)
            for m in titles:
                title_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                if start is None:
                    if '사업의 내용' in title_text:
                        start = m.end()
                else:
                    end = m.start()
                    break

            if start is None:
                print("--- '사업의 내용' 섹션을 보고서에서 찾지 못했습니다.")
                return None

            section_html = text[start:end]
            section_text = re.sub(r'<[^>]+>', '\n', section_html)
            section_text = html.unescape(section_text)
            section_text = re.sub(r'[ \t]+', ' ', section_text)
            section_text = re.sub(r'\n\s*\n+', '\n', section_text).strip()

            # AI 프롬프트 길이 제한을 고려한 트리밍
            max_len = 12000
            if len(section_text) > max_len:
                section_text = section_text[:max_len] + "\n... (이하 생략)"

            return section_text
        except Exception as e:
            print(f"DART Document API Error: {e}")
            return None

dart_service = DartService()
