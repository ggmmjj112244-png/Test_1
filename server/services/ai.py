import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class AIService:
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            # 모델명을 명시적으로 지정
            self.model = genai.GenerativeModel('models/gemini-1.5-flash')
        else:
            self.model = None

    def summarize_corporate_info_stream(self, corp_name, dart_content, news_content):
        """DART와 뉴스 데이터를 바탕으로 기업 정보를 실시간으로 요약합니다."""
        if not self.model:
            yield "Gemini API Key가 설정되지 않았습니다."
            return

        prompt = f"""
너는 전문 주식 분석가이자 기업 리서치 전문가야. 
아래 제공된 [DART 사업보고서 내용]과 [최신 뉴스 데이터]를 바탕으로 '{corp_name}'에 대한 기업 정보를 요약해줘.

[작성 규칙]
1. 반드시 다음 4가지 섹션을 포함해야 함:
   - 이름의 유래와 기업의 역사
   - 무엇을 만드는 회사인가 (주요 사업 및 제품)
   - 산업 내 포지셔닝 및 경쟁력
   - 현재 집중하고 있는 미래 성장 동력
2. 형식: 각 섹션별로 '**[섹션 주제 제목]** - [상세 내용]' 순으로 작성할 것.
3. 내용은 구체적이고 전문적이어야 하며, 제공된 데이터를 최대한 활용할 것.
4. 말투는 격식 있는 문어체를 사용할 것.

[데이터 시작]
DART 사업보고서 요약:
{dart_content}

최신 뉴스 및 리포트 요약:
{news_content}
[데이터 끝]
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
