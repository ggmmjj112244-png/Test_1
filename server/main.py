import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .services.dart import dart_service
from .services.naver import naver_service
from .services.ai import ai_service

app = FastAPI()

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"서버 내부 오류: {str(exc)}"}
    )

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from pydantic import BaseModel
from typing import List

class SummarizeRequest(BaseModel):
    corp_name: str
    selected_items: List[str]

@app.get("/fetch_full_content")
async def fetch_full_content(url: str):
    """URL의 본문 내용을 최대한 전문으로 추출하여 반환합니다."""
    if not url or url == "#" or "youtube.com" in url:
        return {"status": "error", "message": "본문을 추출할 수 없는 링크입니다."}
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import re

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 인코딩 처리
        content_type = response.headers.get('content-type', '').lower()
        if 'charset' not in content_type:
            response.encoding = response.apparent_encoding
        
        # lxml 대신 html.parser 사용 (호환성)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 불필요한 태그 제거
        for s in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'iframe', 'button', 'input', 'form', 'meta']):
            s.decompose()
            
        content_selectors = [
            '#dic_area', '#articleBodyContents', '#newsct_article', '.newsct_article',
            '#articeBody', '#articleBody', '.article_body', '.article-body',
            '#content', '.post-content', '.post_content', '.entry-content',
            '.viewer_content', '.se-main-container', '.post_article',
            'article', 'main', '#main-content', '.main-content'
        ]
        
        content_text = ""
        for selector in content_selectors:
            found = soup.select_one(selector)
            if found:
                for extra in found.select('.comment, .reply, .ad, .social, .tag, .share'):
                    extra.decompose()
                content_text = found.get_text(separator='\n', strip=True)
                if len(content_text) > 300: break
        
        if not content_text:
            p_tags = soup.find_all('p')
            content_text = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 30])

        content_text = re.sub(r'\n\s*\n+', '\n\n', content_text).strip()

        if not content_text or len(content_text) < 100:
            return {"status": "error", "message": "본문 내용을 충분히 추출하지 못했습니다."}
            
        return {"status": "success", "content": content_text}
        
    except Exception as e:
        print(f"Error in fetch_full_content: {e}")
        return {"status": "error", "message": f"본문 추출 중 오류: {str(e)}"}

@app.get("/search")
async def search_info(corp_name: str):
    """기업 관련 정보를 검색하여 목록을 반환합니다."""
    try:
        # 1. DART 기업 코드 조회
        corp_code = dart_service.get_corp_code(corp_name)
        if not corp_code:
            return {"status": "error", "message": f"'{corp_name}' 기업 코드를 찾을 수 없습니다. (DART API 키 확인 필요)"}

        # 2. DART 기업 개요
        dart_info = dart_service.get_company_overview(corp_code)
        
        # 3. 네이버 뉴스 검색
        news_items = naver_service.search_news(corp_name, display=10)
        biz_news_items = naver_service.search_news(f"{corp_name} 사업", display=5)
        report_items = naver_service.search_reports(corp_name)
        blog_items = naver_service.search_blog(corp_name, display=5)
        cafe_items = naver_service.search_cafe(corp_name, display=5)

        results = []
        if dart_info and "수집할 수 없습니다" not in dart_info:
            results.append({"id": "dart_0", "type": "DART", "title": "[공시] 기업 개요 및 주요 사업", "content": dart_info})

        for i, item in enumerate(news_items + biz_news_items):
            results.append({"id": f"news_{i}", "type": "NEWS", "title": item['title'], "content": item['description'], "link": item.get('link', '#')})

        for i, item in enumerate(blog_items):
            results.append({"id": f"blog_{i}", "type": "BLOG", "title": item['title'], "content": item['description'], "link": item.get('link', '#')})

        for i, item in enumerate(cafe_items):
            results.append({"id": f"cafe_{i}", "type": "CAFE", "title": item['title'], "content": item['description'], "link": item.get('link', '#')})

        for i, item in enumerate(report_items):
            results.append({"id": f"report_{i}", "type": "REPORT", "title": f"[리서치] {item['title']}", "content": item['description'], "link": item.get('link', '#')})

        results.append({"id": "youtube_0", "type": "YOUTUBE", "title": f"{corp_name} 관련 유튜브 검색 결과", "content": "유튜브에서 최신 영상 및 분석 자료를 직접 확인해보세요.", "link": f"https://www.youtube.com/results?search_query={corp_name}"})

        return {"status": "success", "items": results}
    except Exception as e:
        print(f"Error in /search: {e}")
        return {"status": "error", "message": f"검색 중 서버 오류 발생: {str(e)}"}

@app.post("/summarize")
async def summarize_selected(request: SummarizeRequest):
    """선택된 정보를 바탕으로 요약을 수행합니다."""
    async def event_generator():
        yield json.dumps({"status": "progress", "message": "선택된 정보를 분석하여 요약을 생성 중입니다..."}) + "\n"
        
        full_content = "\n\n".join(request.selected_items)
        
        full_summary = ""
        for chunk in ai_service.summarize_corporate_info_stream(request.corp_name, "선택된 요약 정보 세트", full_content):
            full_summary += chunk
            yield json.dumps({"status": "partial", "data": {"summary": full_summary}}) + "\n"
        
        yield json.dumps({"status": "complete", "data": {"summary": full_summary}}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.get("/analyze")
async def analyze_company(corp_name: str):
    async def event_generator():
        # 1단계: DART 기업 코드 조회
        yield json.dumps({"status": "progress", "message": f"DART에서 '{corp_name}' 기업 코드를 조회하고 있습니다..."}) + "\n"
        await asyncio.sleep(0.5)
        corp_code = dart_service.get_corp_code(corp_name)
        
        if not corp_code:
            yield json.dumps({"status": "error", "message": f"'{corp_name}'에 해당하는 기업 코드를 찾을 수 없습니다."}) + "\n"
            return

        # 2단계: DART 데이터 수집 (개요 정보 추가)
        yield json.dumps({"status": "progress", "message": "DART 기업 정보를 수집하고 있습니다..."}) + "\n"
        dart_info = dart_service.get_company_overview(corp_code)
        rcept_no = dart_service.get_latest_report(corp_code)
        dart_summary = f"DART 기업정보: {dart_info}\n최근 보고서 번호: {rcept_no}"
        await asyncio.sleep(0.5)

        # 3단계: 네이버 뉴스 수집 (검색어 최적화 및 최신순 정렬)
        yield json.dumps({"status": "progress", "message": "최신 뉴스 및 시장 리포트를 분석하고 있습니다..."}) + "\n"
        # '삼성전자' 키워드로 최신 뉴스 검색
        news_items = naver_service.search_news(corp_name)
        # '삼성전자 리포트/전망' 키워드로 추가 검색
        report_items = naver_service.search_reports(corp_name)
        
        all_news = news_items + report_items
        news_content = "\n".join([f"- {item['title']}: {item['description']}" for item in all_news])
        await asyncio.sleep(0.5)

        # 4단계: Gemini AI 요약 (스트리밍 적용)
        yield json.dumps({"status": "progress", "message": "Gemini AI가 정보를 분석하여 요약하고 있습니다. 잠시만 기다려 주세요..."}) + "\n"
        
        full_summary = ""
        # AI 요약 내용을 실시간으로 전달하기 위한 status: partial 추가
        for chunk in ai_service.summarize_corporate_info_stream(corp_name, dart_summary, news_content):
            full_summary += chunk
            yield json.dumps({"status": "partial", "data": {"summary": full_summary}}) + "\n"
        
        # 5단계: 최종 완료 결과 전송
        yield json.dumps({
            "status": "complete", 
            "data": {
                "summary": full_summary,
                "sources": {
                    "dart": f"https://opendart.fss.or.kr/reporting/viewer.do?rcpNo={rcept_no}" if rcept_no else "정보 없음",
                    "news": f"https://search.naver.com/search.naver?query={corp_name}+뉴스"
                }
            }
        }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# 정적 파일 서버 (가장 마지막에 배치)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
