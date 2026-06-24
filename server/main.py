import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .services.dart import dart_service
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


@app.get("/search")
async def search_info(corp_name: str):
    """DART 공시 정보를 검색하여 목록을 반환합니다."""
    try:
        corp_code = dart_service.get_corp_code(corp_name)
        if not corp_code:
            return {"status": "error", "message": f"'{corp_name}' 기업 코드를 찾을 수 없습니다. (DART API 키 확인 필요)"}

        results = []

        # 1. 정기공시 - 사업보고서 (회사의 개요 + 사업의 내용)
        dart_info = dart_service.get_company_overview(corp_code)
        if dart_info and "수집할 수 없습니다" not in dart_info:
            results.append({"id": "dart_annual", "type": "사업보고서", "title": "[정기공시] 사업보고서", "content": dart_info})

        # 2. 발행공시 - 투자설명서
        prospectus = dart_service.get_investment_prospectus(corp_code)
        if prospectus:
            results.append({"id": "dart_prospectus", "type": "투자설명서", "title": "[발행공시] 투자설명서", "content": prospectus})

        # 3. IR / 기업설명회 공시
        ir_materials = dart_service.get_ir_materials(corp_code)
        if ir_materials:
            results.append({"id": "dart_ir", "type": "IR", "title": "[IR] 기업설명회 공시", "content": ir_materials})

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

        # 2단계: DART 데이터 수집
        yield json.dumps({"status": "progress", "message": "DART 사업보고서를 수집하고 있습니다..."}) + "\n"
        dart_info = dart_service.get_company_overview(corp_code)
        rcept_no, _ = dart_service.get_latest_report(corp_code)

        data_blocks = [f"## 사업보고서\n{dart_info}"]

        yield json.dumps({"status": "progress", "message": "투자설명서 및 IR 자료를 수집하고 있습니다..."}) + "\n"
        prospectus = dart_service.get_investment_prospectus(corp_code)
        if prospectus:
            data_blocks.append(prospectus)

        ir_materials = dart_service.get_ir_materials(corp_code)
        if ir_materials:
            data_blocks.append(ir_materials)
        await asyncio.sleep(0.5)

        combined_data = "\n\n".join(data_blocks)
        await asyncio.sleep(0.5)

        # 3단계: Gemini AI 요약 (스트리밍 적용)
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
                    "dart": f"https://opendart.fss.or.kr/reporting/viewer.do?rcpNo={rcept_no}" if rcept_no else "정보 없음"
                }
            }
        }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# 정적 파일 서버 (가장 마지막에 배치)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
