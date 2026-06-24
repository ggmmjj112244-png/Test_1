import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.5',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# 주요 상장사 IR 페이지 URL
KNOWN_IR_URLS = {
    '카카오': 'https://www.kakaocorp.com/ir/referenceRoom/earningsAnnouncement',
    '카카오뱅크': 'https://ir.kakaobank.com/disclosure/financial-result',
    '현대자동차': 'https://www.hyundai.com/worldwide/ko/company/ir/financial-information/quarterly-earnings',
    '기아': 'https://www.kia.com/kr/company/ir/announcements/financial-results.html',
    '삼성SDI': 'https://www.samsungsdi.co.kr/ir/ir-activity/index.html',
    '삼성바이오로직스': 'https://www.samsungbiologics.com/investors/ir-events.do',
    '현대모비스': 'https://www.mobis.co.kr/kr/ir/financial-results/business.do',
    '포스코홀딩스': 'https://www.poscoholdings.com/kor/inv/finl/quar/quar.do',
    'LG이노텍': 'https://www.lginnotek.com/ir/financial-results.do',
    '두산에너빌리티': 'https://www.doosan.com/ko/business/ir/',
    'SK이노베이션': 'https://www.skinnovation.com/ir/finance/earningReport.do',
    'HD현대': 'https://www.hd.com/kr/ir/financial-information/earnings-release',
}

# 스크래핑이 차단된 기업 - 직접 링크만 제공
IR_LINK_ONLY = {
    '삼성전자': 'https://www.samsung.com/sec/ir/financial-information/earnings-release/',
    'SK하이닉스': 'https://www.skhynix.com/kor/inv/financialInformation.do',
    'LG전자': 'https://www.lg.com/kr/investor-relations/',
    'NAVER': 'https://www.navercorp.com/investment/earningAnnouncement',
    'LG화학': 'https://www.lgchem.com/investor/financial-information/earningsRelease',
    'SK텔레콤': 'https://www.sktelecom.com/kr/investor/financialInfo/earningReleases.do',
}

# IR 페이지 탐색용 공통 경로
COMMON_IR_PATHS = ['/ir', '/ir/', '/investor-relations', '/investors', '/kor/inv', '/ko/ir']


def _decode_response(resp):
    """응답을 올바른 인코딩으로 텍스트 변환."""
    ct = resp.headers.get('Content-Type', '').lower()
    if 'euc-kr' in ct or 'euc_kr' in ct:
        return resp.content.decode('euc-kr', errors='ignore')
    try:
        return resp.content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return resp.content.decode('euc-kr', errors='ignore')
        except Exception:
            return resp.text


def _extract_text(html, max_lines=80):
    """HTML에서 의미있는 IR 텍스트를 추출합니다."""
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
        tag.decompose()

    # 메인 콘텐츠 영역 우선 탐색
    main = (
        soup.find('main')
        or soup.find(id=re.compile(r'(content|main|wrap)', re.I))
        or soup.find(class_=re.compile(r'(content|main|wrap)', re.I))
        or soup.body
    )
    text = main.get_text(separator='\n', strip=True) if main else soup.get_text(separator='\n', strip=True)

    # 의미있는 줄만 필터링 (8자 이상, 메뉴/copyright 제외)
    noise = re.compile(r'(copyright|©|all rights reserved|skip to|바로가기|쿠키|cookie)', re.I)
    lines = [
        l for l in text.split('\n')
        if len(l.strip()) >= 8 and not noise.search(l)
    ]
    return '\n'.join(lines[:max_lines])


def _fetch_ir_page(url):
    """URL에서 IR 콘텐츠를 가져옵니다. 성공하면 (text, url) 반환, 실패 시 (None, url)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return None, url
        text = _extract_text(_decode_response(resp))
        if len(text) < 150:
            return None, url
        return text, url
    except Exception:
        return None, url


def get_ir_content(corp_name, hm_url, max_len=3000):
    """
    기업명과 홈페이지 URL로 IR 자료를 수집합니다.
    Returns: (content_text, ir_page_url, is_link_only)
      - content_text: 스크래핑된 IR 텍스트 (없으면 None)
      - ir_page_url: IR 페이지 URL
      - is_link_only: True면 스크래핑 불가 → 링크만 제공
    """
    # 1. 스크래핑 차단 기업 → 링크만 제공
    link_url = IR_LINK_ONLY.get(corp_name)
    if link_url:
        return None, link_url, True

    # 2. 알려진 IR URL로 스크래핑 시도
    known_url = KNOWN_IR_URLS.get(corp_name)
    if known_url:
        text, url = _fetch_ir_page(known_url)
        if text:
            return text[:max_len], url, False

    # 3. hm_url + 공통 경로로 탐색
    if hm_url:
        base = hm_url.rstrip('/')
        if not base.startswith('http'):
            base = 'https://' + base
        for path in COMMON_IR_PATHS:
            text, url = _fetch_ir_page(base + path)
            if text:
                return text[:max_len], url, False

    # 4. 알려진 URL이 있지만 스크래핑 실패한 경우 → 링크만
    if known_url:
        return None, known_url, True

    return None, None, False
