import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class AIService:
    def __init__(self):
        self._initialize_model()

    def _initialize_model(self):
        self.model = None
        if not GEMINI_API_KEY:
            print("Error: GEMINI_API_KEY is missing.")
            return

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            
            # 실제 가용한 모델 목록 가져오기
            available_models = [m.name for m in genai.list_models() 
                               if 'generateContent' in m.supported_generation_methods]
            
            print(f"--- Available Models: {available_models}")

            # 우선순위 후보군 (2.5 Pro는 현재 키에서 무료 등급 접근이 불가하여 2.5 Flash를 최우선으로 사용)
            candidates = [
                'models/gemini-2.5-flash',
                'gemini-2.5-flash',
                'models/gemini-2.0-flash',
                'models/gemini-1.5-flash',
                'gemini-2.0-flash',
                'gemini-1.5-flash'
            ]

            selected = None
            for cand in candidates:
                # 정확히 일치하거나 포함되는 모델 찾기
                for am in available_models:
                    if cand == am or cand.split('/')[-1] == am.split('/')[-1]:
                        selected = am
                        break
                if selected: break

            if not selected and available_models:
                selected = available_models[0] # 최후의 수단: 첫 번째 가용 모델 선택

            if selected:
                print(f"--- Successfully Selected Model: {selected}")
                self.model = genai.GenerativeModel(selected)
            else:
                print("Error: No suitable Gemini models found.")

        except Exception as e:
            print(f"Error during Gemini initialization: {str(e)}")

    def summarize_corporate_info_stream(self, corp_name, dart_content, news_content):
        """DART와 뉴스 데이터를 바탕으로 기업 정보를 실시간으로 요약합니다."""
        # 모델이 없으면 재시도 (환경 변수 반영 지연 등 대비)
        if not self.model:
            self._initialize_model()
            
        if not self.model:
            yield "현재 사용 가능한 Gemini AI 모델을 찾을 수 없습니다. API 키의 권한이나 Google AI Studio 설정을 확인해주세요."
            return

        prompt = f"""[시스템 프롬프트]

당신은 국내 상장기업을 분석하는 전문 애널리스트입니다.
아래 제공된 [데이터]를 바탕으로, 일반 투자자가 '{corp_name}'의 본질을
직관적으로 이해할 수 있도록 분석 보고서를 작성합니다.

아래 8개 섹션을 반드시 포함하여 작성하세요.
각 섹션은 제목과 2~4개의 소제목으로 구성하며,
소제목마다 3~5문장의 해설을 작성합니다.
단순 사실 나열이 아닌, 왜 중요한지 의미와 맥락을 설명하세요.
[데이터]에 없는 내용은 추측하지 말고, 해당 섹션에서 다루지 않거나
"제공된 자료에서 확인되지 않음"이라고 명시하세요.

[출력 섹션]
1. 기업 개요 및 역사 - 설립 배경, 지배구조, 그룹 내 위치
2. 핵심 사업 구조 - 주력 제품/서비스, 매출 비중, 밸류체인
3. 산업 내 포지셔닝 - 시장점유율, 경쟁사 대비 차별점
4. 최근 실적 및 재무 건전성 - 매출/영업이익 흐름, 부채비율, 배당
5. 성장 동력 - 신사업, 투자 계획, 기술 개발
6. 리스크 요인 - 업황 리스크, 지정학, 규제, 경쟁 심화
7. 주요 이슈 및 뉴스 - 최근 6개월 핵심 이슈
8. 투자 포인트 요약 - 핵심 3가지를 불릿으로

[작성 스타일]
- 전문적이되 읽기 쉽게
- 숫자와 구체적 근거를 반드시 포함
- 섹션마다 독자가 "왜 이게 중요한가"를 이해할 수 있게 작성
- 분량: 섹션당 200~300자
- 형식: 각 섹션은 '## 섹션 제목', 소제목은 '### 소제목' 마크다운으로 작성

[데이터]
{dart_content}
{news_content}
"""
        response = self.model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def summarize_corporate_info(self, corp_name, dart_content, news_content):
        """DART와 뉴스 데이터를 바탕으로 기업 정보를 요약합니다. (동기 방식)"""
        if not self.model:
            return "Gemini API Key가 설정되지 않았습니다."

        # 기존 로직 유지 (필요시)
        response = self.model.generate_content(f"Summarize {corp_name} based on provided data.")
        return response.text

ai_service = AIService()
