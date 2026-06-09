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

        # 2단계: DART 사업 내용 수집
        yield json.dumps({"status": "progress", "message": "사업보고서 데이터를 수집하고 있습니다..."}) + "\n"
        # 여기서는 간단히 rcept_no 정도만 가져오는 로직으로 대체 (실제 텍스트 추출은 복잡하므로)
        rcept_no = dart_service.get_latest_report(corp_code)
        dart_summary = f"기업코드: {corp_code}, 최근 보고서 번호: {rcept_no}. (상세 내용은 API 제약으로 인해 기본 정보를 바탕으로 분석합니다.)"
        await asyncio.sleep(1)

        # 3단계: 네이버 뉴스 수집
        yield json.dumps({"status": "progress", "message": "최신 뉴스 및 리포트 데이터를 수집하고 있습니다..."}) + "\n"
        news_items = naver_service.search_news(corp_name)
        news_content = "\n".join([f"- {item['title']}: {item['description']}" for item in news_items])
        await asyncio.sleep(1)

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
