import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .services.dart import dart_service
from .services.naver import naver_service
from .services.ai import ai_service

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
