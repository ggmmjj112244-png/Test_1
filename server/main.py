import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .services.dart import dart_service
from .services.naver import naver_service
from .services.ai import ai_service
from .services import web_utils

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

        response = requests.get(url, headers=web_utils.DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        if 'charset' not in content_type:
            response.encoding = response.apparent_encoding

        content_text = web_utils.extract_main_text(response.text)

        if not content_text or len(content_text) < 100:
            return {"status": "error", "message": "본문 내용을 충분히 추출하지 못했습니다."}

        return {"status": "success", "content": content_text}

    except Exception as e:
        print(f"Error in fetch_full_content: {e}")
        return {"status": "error", "message": f"본문 추출 중 오류: {str(e)}"}

def _format_pub_date(pub_date_str):
    """Naver API의 RFC822 날짜 문자열을 'YYYY-MM-DD'로 변환합니다."""
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub_date_str).strftime("%Y-%m-%d")
    except Exception:
        return pub_date_str


@app.get("/search")
async def search_info(corp_name: str):
    """기업 관련 정보를 검색하여 목록을 반환합니다."""
    try:
        # 1. DART 기업 코드 조회
        corp_code = dart_service.get_corp_code(corp_name)
        if not corp_code:
            return {"status": "error", "message": f"'{corp_name}' 기업 코드를 찾을 수 없습니다. (DART API 키 확인 필요)"}

        # 2. DART 기업 개요 및 회사 정보
        dart_info = dart_service.get_company_overview(corp_code)
        company_info = dart_service.get_company_info(corp_code) or {}
        stock_code = company_info.get('stock_code')
        hm_url = company_info.get('hm_url')

        # 3. 네이버 뉴스 검색
        news_items = naver_service.search_news(corp_name, display=10)
        biz_news_items = naver_service.search_news(f"{corp_name} 사업", display=5)
        report_items = naver_service.search_reports(corp_name)
        blog_items = naver_service.search_blog(corp_name, display=5)
        cafe_items = naver_service.search_cafe(corp_name, display=5)

        results = []
        if dart_info and "수집할 수 없습니다" not in dart_info:
            results.append({"id": "dart_0", "type": "DART", "title": "[공시] 기업 개요 및 주요 사업", "content": dart_info})

        # 3-1. DART 주요사항보고서/증권신고서 발췌
        major_filings = dart_service.get_major_filings(corp_code)
        if major_filings:
            results.append({"id": "dart_major_0", "type": "DART_MAJOR", "title": "[공시] 최근 주요사항보고서/증권신고서", "content": major_filings})

        # 3-2. 네이버 증권 - 기업현황/매출구성/종목뉴스 (정성적 정보)
        if stock_code:
            stock_info = naver_service.get_stock_info(stock_code)
            if stock_info:
                results.append({"id": "stock_0", "type": "STOCK", "title": "[네이버 증권] 기업현황 및 종목뉴스", "content": stock_info})

        # 3-3. 기업 공식 홈페이지 - IR/뉴스룸/회사소개
        if hm_url:
            site_summary = web_utils.get_company_site_summary(hm_url)
            if site_summary:
                results.append({"id": "ir_0", "type": "IR", "title": "[기업 홈페이지] IR/뉴스룸/회사소개", "content": site_summary})

        all_news = news_items + biz_news_items
        for i, item in enumerate(all_news):
            date_str = _format_pub_date(item.get('pubDate', ''))
            content = f"[{date_str}] {item['description']}" if date_str else item['description']

            # 상위 3건은 본문 전문을 추가로 가져와 함께 제공
            if i < 3:
                full_text = web_utils.fetch_url_text(item.get('link', '#'), max_len=1500)
                if full_text:
                    content += f"\n\n[본문]\n{full_text}"

            results.append({"id": f"news_{i}", "type": "NEWS", "title": item['title'], "content": content, "link": item.get('link', '#')})

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

        # 2단계: DART 데이터 수집 (개요/사업내용 + 주요사항보고서/증권신고서)
        yield json.dumps({"status": "progress", "message": "DART 기업 정보를 수집하고 있습니다..."}) + "\n"
        dart_info = dart_service.get_company_overview(corp_code)
        rcept_no = dart_service.get_latest_report(corp_code)
        company_info = dart_service.get_company_info(corp_code) or {}
        stock_code = company_info.get('stock_code')
        hm_url = company_info.get('hm_url')

        data_blocks = [f"## DART 기업 개요 및 사업의 내용\n{dart_info}"]

        major_filings = dart_service.get_major_filings(corp_code)
        if major_filings:
            data_blocks.append(major_filings)
        await asyncio.sleep(0.5)

        # 3단계: 네이버 증권/뉴스/리포트 수집
        yield json.dumps({"status": "progress", "message": "최신 뉴스 및 시장 정보를 분석하고 있습니다..."}) + "\n"

        if stock_code:
            stock_info = naver_service.get_stock_info(stock_code)
            if stock_info:
                data_blocks.append(stock_info)

        if hm_url:
            site_summary = web_utils.get_company_site_summary(hm_url)
            if site_summary:
                data_blocks.append(site_summary)

        news_items = naver_service.search_news(corp_name)
        report_items = naver_service.search_reports(corp_name)
        all_news = news_items + report_items

        news_lines = []
        for i, item in enumerate(all_news):
            date_str = _format_pub_date(item.get('pubDate', ''))
            line = f"- [{date_str}] {item['title']}\n  핵심: {item['description']}"
            if i < 3:
                full_text = web_utils.fetch_url_text(item.get('link', '#'), max_len=1500)
                if full_text:
                    line += f"\n  본문: {full_text}"
            news_lines.append(line)

        if news_lines:
            data_blocks.append("## 관련 뉴스\n" + "\n".join(news_lines))

        combined_data = "\n\n".join(data_blocks)
        await asyncio.sleep(0.5)

        # 4단계: Gemini AI 요약 (스트리밍 적용)
        yield json.dumps({"status": "progress", "message": "Gemini AI가 정보를 분석하여 요약하고 있습니다. 잠시만 기다려 주세요..."}) + "\n"

        full_summary = ""
        # AI 요약 내용을 실시간으로 전달하기 위한 status: partial 추가
        for chunk in ai_service.summarize_corporate_info_stream(corp_name, combined_data, ""):
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
