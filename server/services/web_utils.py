import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}

CONTENT_SELECTORS = [
    '#dic_area', '#articleBodyContents', '#newsct_article', '.newsct_article',
    '#articeBody', '#articleBody', '.article_body', '.article-body',
    '#content', '.post-content', '.post_content', '.entry-content',
    '.viewer_content', '.se-main-container', '.post_article',
    'article', 'main', '#main-content', '.main-content'
]

IR_LINK_KEYWORDS = [
    'ir', '투자정보', '투자', '뉴스룸', '보도자료', '사업소개', '회사소개',
    '연혁', 'history', 'newsroom', 'investor', 'about', 'company', 'business'
]


def extract_main_text(html_text, selectors=None):
    """HTML에서 본문으로 추정되는 텍스트를 추출합니다."""
    soup = BeautifulSoup(html_text, 'html.parser')

    for s in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'iframe', 'button', 'input', 'form', 'meta']):
        s.decompose()

    selectors = selectors or CONTENT_SELECTORS
    content_text = ""
    for selector in selectors:
        found = soup.select_one(selector)
        if found:
            for extra in found.select('.comment, .reply, .ad, .social, .tag, .share'):
                extra.decompose()
            content_text = found.get_text(separator='\n', strip=True)
            if len(content_text) > 300:
                break

    if not content_text:
        p_tags = soup.find_all('p')
        content_text = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 30])

    content_text = re.sub(r'\n\s*\n+', '\n\n', content_text).strip()
    return content_text


def fetch_url_text(url, timeout=8, max_len=2000):
    """URL의 본문 텍스트를 가져와 길이를 제한하여 반환합니다. 실패 시 None."""
    if not url or url == "#":
        return None
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        if 'charset' not in content_type:
            response.encoding = response.apparent_encoding

        content_text = extract_main_text(response.text)
        if not content_text or len(content_text) < 100:
            return None

        if len(content_text) > max_len:
            content_text = content_text[:max_len] + "\n... (이하 생략)"

        return content_text
    except Exception as e:
        print(f"--- fetch_url_text Error ({url}): {e}")
        return None


def find_ir_links(homepage_url, timeout=8, max_links=3):
    """기업 홈페이지에서 IR/뉴스룸/회사소개 등 정보성 링크를 찾아 절대 URL 목록을 반환합니다."""
    if not homepage_url:
        return []
    try:
        response = requests.get(homepage_url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        if 'charset' not in content_type:
            response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, 'html.parser')
        base_domain = urlparse(homepage_url).netloc

        candidates = []
        seen = set()
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            text = a.get_text(strip=True).lower()
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue

            haystack = f"{text} {href.lower()}"
            score = sum(1 for kw in IR_LINK_KEYWORDS if kw in haystack)
            if score == 0:
                continue

            absolute = urljoin(homepage_url, href)
            if urlparse(absolute).netloc != base_domain:
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            candidates.append((score, absolute))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [url for _, url in candidates[:max_links]]
    except Exception as e:
        print(f"--- find_ir_links Error ({homepage_url}): {e}")
        return []


def get_company_site_summary(hm_url, max_total_len=3000):
    """기업 공식 홈페이지의 IR/뉴스룸/회사소개 등 정보를 best-effort로 수집합니다."""
    if not hm_url:
        return None

    if not hm_url.startswith('http'):
        hm_url = f"https://{hm_url}"

    links = find_ir_links(hm_url)
    if not links:
        return None

    blocks = []
    total_len = 0
    for link in links:
        text = fetch_url_text(link, max_len=1500)
        if not text:
            continue
        block = f"## 기업 홈페이지 정보 (출처: {link})\n{text}"
        if total_len + len(block) > max_total_len:
            remaining = max_total_len - total_len
            if remaining <= 0:
                break
            block = block[:remaining] + "\n... (이하 생략)"
        blocks.append(block)
        total_len += len(block)
        if total_len >= max_total_len:
            break

    if not blocks:
        return None

    return "\n\n".join(blocks)
