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
        url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={self.api_key}"
        response = requests.get(url)
        
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                xml_data = z.read('CORPCODE.xml')
                tree = ET.fromstring(xml_data)
                for corp in tree.findall('list'):
                    name = corp.find('corp_name').text
                    code = corp.find('corp_code').text
                    self.corp_codes[name] = code
            return True
        return False

    def get_corp_code(self, corp_name):
        """기업명으로 고유번호를 반환합니다."""
        if not self.corp_codes:
            self.update_corp_codes()
        return self.corp_codes.get(corp_name)

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

    def get_company_overview(self, corp_code):
        """회사의 개요를 가져옵니다."""
        # 실제로는 rcept_no가 필요할 수도 있으나, 최신 보고서 기준 API 호출
        rcept_no = self.get_latest_report(corp_code)
        if not rcept_no: return ""
        
        # OpenDART의 단일인증키 기반 상세 추출 (예시 파라미터)
        # 실제 API 명세에 맞춰 수정 필요
        return f"상세 데이터 수집 중 (rcept_no: {rcept_no})"

    def get_business_content(self, corp_code):
        """사업의 내용을 가져옵니다."""
        rcept_no = self.get_latest_report(corp_code)
        if not rcept_no: return ""
        return f"사업 상세 데이터 수집 중 (rcept_no: {rcept_no})"

dart_service = DartService()
