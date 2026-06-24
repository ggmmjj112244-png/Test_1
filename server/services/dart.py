import os
import re
import html
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")

class DartService:
    def __init__(self):
        self.api_key = DART_API_KEY
        self.corp_codes = {}        # {corp_name: corp_code}
        self.corp_stock_codes = {}  # {corp_name: stock_code}  상장사 여부 판단용

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
                        stock_el = corp.find('stock_code')
                        stock_code = (stock_el.text or '').strip() if stock_el is not None else ''
                        self.corp_codes[name] = code
                        if stock_code:
                            self.corp_stock_codes[name] = stock_code
                        count += 1
                    print(f"--- Successfully loaded {count} corp codes ({len(self.corp_stock_codes)} listed).")
                return True
            else:
                print(f"--- Failed to download corp codes: {response.text}")
        except Exception as e:
            print(f"--- Error updating corp codes: {str(e)}")
        return False

    def get_corp_code(self, corp_name):
        """기업명으로 고유번호를 반환합니다. 상장사 우선, 이름이 짧을수록 우선합니다."""
        if not self.corp_codes:
            print("--- Corp codes cache is empty. Updating...")
            self.update_corp_codes()

        # 1. 정확히 일치
        code = self.corp_codes.get(corp_name)
        if code:
            return code

        # 2. 대소문자 무시 정확 일치 (NAVER, kakao 등 영문 사명)
        corp_upper = corp_name.upper()
        for name, c in self.corp_codes.items():
            if name.upper() == corp_upper:
                print(f"--- Found case-insensitive match: {name} -> {c}")
                return c

        # 3. 앞자리 일치(prefix) - 상장사 우선, 짧은 이름 우선
        prefix_matches = [(name, c) for name, c in self.corp_codes.items()
                          if name.startswith(corp_name) or name.upper().startswith(corp_upper)]
        if prefix_matches:
            prefix_matches.sort(key=lambda x: (x[0] not in self.corp_stock_codes, len(x[0])))
            name, c = prefix_matches[0]
            print(f"--- Found prefix match: {name} -> {c}")
            return c

        # 4. 부분 일치 - 상장사 우선, 짧은 이름 우선
        substr_matches = [(name, c) for name, c in self.corp_codes.items()
                          if corp_name in name or corp_upper in name.upper()]
        if substr_matches:
            substr_matches.sort(key=lambda x: (x[0] not in self.corp_stock_codes, len(x[0])))
            name, c = substr_matches[0]
            print(f"--- Found substring match: {name} -> {c}")
            return c

        return None

    def get_latest_report(self, corp_code):
        """최신 사업보고서의 rcept_no를 가져옵니다."""
        bgn_de = (datetime.now() - timedelta(days=365 * 3)).strftime('%Y%m%d')
        url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={self.api_key}&corp_code={corp_code}&pblntf_ty=A&bgn_de={bgn_de}"
        try:
            response = requests.get(url, timeout=10).json()
            if response.get('status') == '000':
                for item in response.get('list', []):
                    if "사업보고서" in item.get('report_nm', ''):
                        return item.get('rcept_no'), item.get('report_nm')
        except Exception as e:
            print(f"DART List API Error: {e}")
        return None, None

    def get_company_info(self, corp_code):
        """DART 기업개요 API에서 기업 기본 정보를 가져옵니다."""
        url = f"https://opendart.fss.or.kr/api/company.json?crtfc_key={self.api_key}&corp_code={corp_code}"
        try:
            response = requests.get(url, timeout=10).json()
            if response.get('status') == '000':
                est_dt = response.get('est_dt', '')
                if len(est_dt) == 8:
                    est_dt = f"{est_dt[:4]}-{est_dt[4:6]}-{est_dt[6:]}"
                return {
                    "corp_name": response.get('corp_name'),
                    "ceo_nm": response.get('ceo_nm'),
                    "induty_code": response.get('induty_code'),
                    "hm_url": response.get('hm_url'),
                    "phn_no": response.get('phn_no'),
                    "fax_no": response.get('fax_no'),
                    "stock_code": response.get('stock_code', '').strip(),
                    "est_dt": est_dt,
                    "acc_mt": response.get('acc_mt'),
                    "adres": response.get('adres'),
                }
        except Exception as e:
            print(f"DART Company Info API Error: {e}")
        return None

    def get_company_overview(self, corp_code):
        """기업 기본정보 + 최신 사업보고서(회사의 개요 + 사업의 내용)를 반환합니다."""
        info = self.get_company_info(corp_code)
        if not info:
            return "기업 정보를 수집할 수 없습니다."

        rcept_no, report_nm = self.get_latest_report(corp_code)

        overview = f"### [기업 기본 정보: {info['corp_name']}]\n\n"
        overview += f"- **대표이사**: {info.get('ceo_nm', '정보 없음')}\n"
        overview += f"- **업종 코드**: {info.get('induty_code', '정보 없음')}\n"
        overview += f"- **설립일**: {info.get('est_dt', '정보 없음')}\n"
        overview += f"- **결산월**: {info.get('acc_mt', '정보 없음')}월\n"
        overview += f"- **주소**: {info.get('adres', '정보 없음')}\n"
        overview += f"- **홈페이지**: {info.get('hm_url', '정보 없음')}\n"

        if rcept_no:
            section_content = self.extract_sections(rcept_no, ['회사의 개요', '사업의 내용'], max_len=12000)
            overview += f"\n### [{report_nm} (접수번호: {rcept_no})]\n\n"
            if section_content:
                overview += section_content
            else:
                overview += "사업보고서 원문에서 섹션을 추출하지 못했습니다.\n"
        else:
            overview += "\n최신 사업보고서를 찾지 못했습니다.\n"

        return overview

    def get_investment_prospectus(self, corp_code):
        """최근 3년 이내 투자설명서를 가져옵니다 (발행공시 C)."""
        bgn_de = (datetime.now() - timedelta(days=365 * 3)).strftime('%Y%m%d')
        url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={self.api_key}&corp_code={corp_code}&pblntf_ty=C&bgn_de={bgn_de}"
        try:
            resp = requests.get(url, timeout=10).json()
            if resp.get('status') != '000':
                return None
            items = [i for i in resp.get('list', []) if '투자설명서' in i.get('report_nm', '')]
            if not items:
                return None

            blocks = []
            total_len = 0
            for item in items[:3]:
                section = self.extract_sections(
                    item['rcept_no'],
                    ['모집 또는 매출에 관한 일반사항', '투자위험요소', '자금의 사용목적'],
                    max_len=4000
                )
                if section:
                    block = f"### [{item['report_nm']} ({item['rcept_dt']})]\n\n{section}"
                else:
                    block = f"- {item['report_nm']} ({item['rcept_dt']})"

                blocks.append(block)
                total_len += len(block)
                if total_len >= 8000:
                    break

            if not blocks:
                return None
            return "## 투자설명서\n\n" + "\n\n".join(blocks)
        except Exception as e:
            print(f"DART Prospectus Error: {e}")
            return None

    def get_ir_materials(self, corp_code):
        """기업 IR 자료를 수집합니다. 공식 IR 홈페이지 스크래핑 우선, DART 공시 목록 보완.
        Returns: (content_text, ir_page_url)
        """
        from .ir_scraper import get_ir_content

        info = self.get_company_info(corp_code)
        corp_name = info.get('corp_name', '') if info else ''
        hm_url = info.get('hm_url', '') if info else ''

        ir_text, ir_url, is_link_only = get_ir_content(corp_name, hm_url)

        # DART 기업설명회 공시 목록도 병행 수집
        dart_ir_list = self._get_dart_ir_list(corp_code)

        result_parts = []

        if ir_text:
            result_parts.append(f"## IR 자료 (공식 IR 홈페이지)\n\n{ir_text}")
        elif is_link_only and ir_url:
            result_parts.append(
                f"## IR 자료 링크\n\n해당 기업의 공식 IR 홈페이지에서 실적발표 자료를 직접 확인하세요.\n- **IR 홈페이지**: {ir_url}"
            )

        if dart_ir_list:
            result_parts.append(dart_ir_list)

        if not result_parts:
            return None, ir_url

        content = "\n\n".join(result_parts)
        return content, ir_url

    def _get_dart_ir_list(self, corp_code):
        """DART에서 최근 2년 기업설명회 공시 목록을 가져옵니다."""
        bgn_de = (datetime.now() - timedelta(days=365 * 2)).strftime('%Y%m%d')
        url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={self.api_key}&corp_code={corp_code}&bgn_de={bgn_de}"
        try:
            resp = requests.get(url, timeout=10).json()
            if resp.get('status') != '000':
                return None
            ir_keywords = ['기업설명회', 'IR', '투자자설명회', '기업설명']
            items = [i for i in resp.get('list', [])
                     if any(k in i.get('report_nm', '') for k in ir_keywords)]
            if not items:
                return None
            lines = [f"- **{i['report_nm']}** (공시일: {i['rcept_dt']})" for i in items[:8]]
            return "### DART 기업설명회 공시 목록\n\n" + "\n".join(lines)
        except Exception as e:
            print(f"DART IR List Error: {e}")
            return None

    def _get_filing_list(self, corp_code, pblntf_ty, label, limit=2, name_filter=None):
        """list.json에서 특정 공시유형의 최근(bgn_de 이후) 보고서 목록을 가져옵니다."""
        bgn_de = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={self.api_key}&corp_code={corp_code}&pblntf_ty={pblntf_ty}&bgn_de={bgn_de}"
        try:
            response = requests.get(url, timeout=10).json()
            if response.get('status') != '000':
                return []
            results = []
            for item in response.get('list', []):
                report_nm = item.get('report_nm', '')
                if name_filter and name_filter not in report_nm:
                    continue
                results.append({
                    "report_nm": report_nm,
                    "rcept_no": item.get('rcept_no'),
                    "rcept_dt": item.get('rcept_dt')
                })
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            print(f"--- DART List API Error ({label}): {e}")
            return []

    def _clean_html_text(self, raw_html):
        """HTML 태그를 제거하고 텍스트를 정리합니다."""
        text = re.sub(r'<[^>]+>', '\n', raw_html)
        text = html.unescape(text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n', text).strip()
        return text

    def _pick_main_xml(self, z):
        """zip 파일에서 메인 문서(가장 큰) XML 파일명을 반환합니다."""
        xml_files = [n for n in z.namelist() if n.lower().endswith('.xml')]
        if not xml_files:
            return None
        return max(xml_files, key=lambda n: z.getinfo(n).file_size)

    def _decode_raw(self, raw):
        """바이트 데이터를 텍스트로 디코딩합니다. UTF-8 우선, 실패 시 CP949."""
        for enc in ['utf-8', 'cp949']:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode('utf-8', errors='ignore')

    def _extract_full_text(self, rcept_no, max_len=2000):
        """DART 보고서 원문 전체를 텍스트로 추출합니다."""
        if not rcept_no:
            return None
        url = f"https://opendart.fss.or.kr/api/document.xml?crtfc_key={self.api_key}&rcept_no={rcept_no}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return None
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                xml_name = self._pick_main_xml(z)
                if not xml_name:
                    return None
                raw = z.read(xml_name)
            text = self._decode_raw(raw)
            result = self._clean_html_text(text)
            if len(result) > max_len:
                result = result[:max_len] + "\n... (이하 생략)"
            return result or None
        except Exception as e:
            print(f"DART Full Text Extract Error: {e}")
            return None

    def extract_sections(self, rcept_no, section_titles, max_len=12000):
        """DART 보고서에서 로마자 대제목(I, II ...) 기준으로 지정된 섹션 전체를 추출합니다."""
        if not rcept_no:
            return None

        url = f"https://opendart.fss.or.kr/api/document.xml?crtfc_key={self.api_key}&rcept_no={rcept_no}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print(f"--- DART Document API HTTP Error: {response.status_code}")
                return None

            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                xml_name = self._pick_main_xml(z)
                if not xml_name:
                    return None
                raw = z.read(xml_name)

            text = self._decode_raw(raw)

            titles = list(re.finditer(r'<TITLE[^>]*>(.*?)</TITLE>', text, re.IGNORECASE | re.DOTALL))
            title_infos = [(m, re.sub(r'<[^>]+>', '', m.group(1)).strip()) for m in titles]

            # 로마자로 시작하는 대제목만 추출 (I. II. III. 등)
            roman_re = re.compile(r'^[IVXLCDM]+\.\s')
            major_sections = [(i, m, tt) for i, (m, tt) in enumerate(title_infos) if roman_re.match(tt)]

            parts = []

            if major_sections:
                for j, (i, m, tt) in enumerate(major_sections):
                    if any(target in tt for target in section_titles):
                        end = major_sections[j + 1][1].start() if j + 1 < len(major_sections) else len(text)
                        section_text = self._clean_html_text(text[m.end():end])
                        if section_text:
                            parts.append(f"#### {tt}\n\n{section_text}")
            else:
                # 대제목 구조가 없으면 소제목 기준으로 fallback
                for idx, (m, tt) in enumerate(title_infos):
                    if any(target in tt for target in section_titles):
                        end = title_infos[idx + 1][0].start() if idx + 1 < len(title_infos) else len(text)
                        section_text = self._clean_html_text(text[m.end():end])
                        if section_text:
                            parts.append(f"#### {tt}\n\n{section_text}")

            if not parts:
                return None

            combined = "\n\n".join(parts)
            if len(combined) > max_len:
                combined = combined[:max_len] + "\n... (이하 생략)"
            return combined

        except Exception as e:
            print(f"DART Document API Error: {e}")
            return None

dart_service = DartService()
