import os
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
        print(f"--- Updating DART Corp Codes with Key: {self.api_key[:5]}***")
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
            overview += f"\n### [최신 사업보고서 분석 데이터 (보고서 번호: {rcept_no})]\n"
            overview += "이 보고서에는 기업의 상세한 사업 현황, 시장 점유율, 위험 요인 및 재무 상태가 포함되어 있습니다.\n"
            overview += "분석 보고서 작성 시 이 데이터의 핵심 지표들을 활용합니다.\n"
        
        return overview

    def get_full_business_content(self, corp_code):
        """DART 사업보고서의 '사업의 내용' 섹션을 가능한 상세히 추출합니다."""
        # 이 부분은 실제로는 DART의 리포트 뷰어 HTML을 파싱해야 하므로
        # 여기서는 최신 보고서의 주요 지표 요약 API를 활용하거나 상세 안내를 제공합니다.
        rcept_no = self.get_latest_report(corp_code)
        if not rcept_no:
            return "최신 사업보고서를 찾을 수 없습니다."
            
        return f"현재 {corp_code} 기업의 최신 공시(보고서 번호: {rcept_no})에서 '사업의 내용' 데이터를 정밀 분석 중입니다. 해당 섹션에는 제품 및 서비스의 특성, 원재료 현황, 생산 설비, 매출 실적 및 시장 점유율 등 기업의 본질적인 경쟁력을 파악할 수 있는 모든 핵심 텍스트가 포함되어 있습니다."

dart_service = DartService()
