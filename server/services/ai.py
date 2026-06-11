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

            # 우선순위 후보군 (Gemini Pro 결제 시 무료로 사용 가능한 2.5 Pro를 최우선으로 사용)
            candidates = [
                'models/gemini-2.5-pro',
                'gemini-2.5-pro',
                'models/gemini-2.5-flash',
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

        prompt = f"""너는 전문 주식 분석가이자 기업 리서치 전문가야.
아래 제공된 [데이터]를 바탕으로 '{corp_name}'에 대한 기업 분석 보고서를 작성해줘.

[작성 지침]
1. 고정된 섹션 대신, 제공된 정보에서 도출할 수 있는 해당 기업만의 특징적인 내용을 바탕으로 자유롭게 섹션을 구성해줘.
2. 섹션 제목은 반드시 한 줄로 명확하게 작성할 것.
3. 주요 포함 내용:
   - 해당 기업이 구체적으로 어떤 사업을 영위하고 있는가?
   - 해당 사업의 전문성을 확보하기 위해 그동안 어떠한 역사적 행보와 노력을 기울여 왔는가?
   - 동종 업계 내에서 이 기업만이 가진 독보적인 강점이나 경쟁력은 무엇인가?
4. 제외 사항:
   - 공장 증설, 특정 분기 영업이익 증감, 단기적인 수주 소식 등 단기적인 시간 요소가 포함된 정보는 배제할 것.
   - 장기적인 기업의 가치와 본질에 집중할 것.
5. 마지막 문단은 반드시 '결론'에 해당하는 내용을 작성하되, 제목은 내용에 어울리는 자유로운 형식의 한 줄 제목으로 작성할 것.
6. 말투는 격식 있는 문어체를 사용할 것.
7. 형식: 각 섹션별로 '**[자유로운 섹션 제목]**\n\n[상세 내용]' 순으로 작성할 것.

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
