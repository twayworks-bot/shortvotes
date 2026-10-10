import io
import json
import re
import logging
from typing import List, Optional
from PIL import Image
import google.generativeai as genai

from app.config import settings
from app.schemas.ai_schema import ExtractedMenuItem, AIMenuParseResponse

logger = logging.getLogger(__name__)

# Gemini 클라이언트 초기화
def configure_gemini():
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    else:
        logger.warning("GEMINI_API_KEY is not set in environment or .env file.")

configure_gemini()

SYSTEM_INSTRUCTION = """
당신은 카페 및 음식점의 메뉴판 인식 및 텍스트 데이터 정제 전문가입니다.
사용자가 제공한 메뉴판 이미지 또는 텍스트에서 판매 메뉴 목록을 정확히 추출하고 정제해야 합니다.

[작업 지침]
1. 메뉴 텍스트 추출: 이미지 또는 텍스트 내에서 모든 판매 음료/음식/디저트 항목을 식별합니다.
2. 오타 수정 및 정제:
   - OCR 인식 불량 또는 사용자의 오타(예: '아에리카노', '바닐라라떼e', '밀크티이' 등)를 대한민국 카페/식당 표준 명칭으로 교정합니다.
   - 만약 '기존 등록 메뉴 리스트'가 제공되면, 기존 메뉴명과 유사한 항목은 기존 메뉴의 표기 방식을 우선적으로 존중하여 오타를 맞춥니다.
3. 가격 파싱: 가격(숫자, 원, k 등)이 존재하면 정수 단위로 환산하고, 가격이 없으면 0으로 처리합니다.
4. 카테고리 분류: 커피, 논커피/음료, 에이드/티, 디저트/베이커리, 기타 중 가장 적합한 카테고리를 부여합니다.
5. 출력 형식: 반드시 마크다운 서식이나 추가 설명 없이 유효한 JSON 배열만 출력하세요.

JSON 출력 형식 예시:
[
  {"name": "아메리카노 (HOT)", "price": 4500, "category": "커피"},
  {"name": "카페라떼", "price": 5000, "category": "커피"},
  {"name": "자몽허니블랙티", "price": 5800, "category": "에이드/티"}
]
"""

def clean_json_response(raw_text: str) -> str:
    """마크다운 백틱(```json ... ```) 제거 및 순수 JSON 텍스트 추출"""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 대괄호로 둘러싸인 부분 추출
    match = re.search(r"(\[.*\])", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

def parse_extracted_items(cleaned_text: str) -> List[ExtractedMenuItem]:
    """JSON 텍스트를 ExtractedMenuItem 리스트로 변환"""
    data = json.loads(cleaned_text)
    items = []
    for entry in data:
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        price = entry.get("price", 0)
        try:
            price = int(price)
        except (ValueError, TypeError):
            price = 0
        category = str(entry.get("category", "기본")).strip() or "기본"
        items.append(ExtractedMenuItem(name=name, price=price, category=category))
    return items

class GeminiService:
    @staticmethod
    async def extract_menu_from_image(image_bytes: bytes, existing_menus: Optional[List[str]] = None) -> AIMenuParseResponse:
        """메뉴판 이미지로부터 OCR 및 메뉴 추출, 오타 교정 수행"""
        if not settings.GEMINI_API_KEY:
            return AIMenuParseResponse(
                success=False,
                items=[],
                message="GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요."
            )

        try:
            image = Image.open(io.BytesIO(image_bytes))
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL_NAME,
                generation_config={"max_output_tokens": min(settings.GEMINI_API_MAX_TOKENS, 8192)}
            )

            prompt_parts = [SYSTEM_INSTRUCTION]
            if existing_menus:
                prompt_parts.append(f"기존 등록 메뉴 리스트 참고: {', '.join(existing_menus)}")
            prompt_parts.append("위 메뉴판 이미지에서 메뉴 목록을 추출하고 오타를 교정한 후 JSON 배열로 반환해 주세요.")
            prompt_parts.append(image)

            response = model.generate_content(prompt_parts)
            raw_text = response.text or ""
            cleaned = clean_json_response(raw_text)
            items = parse_extracted_items(cleaned)

            return AIMenuParseResponse(
                success=True,
                items=items,
                raw_response=raw_text,
                message=f"{len(items)}개의 메뉴 항목을 성공적으로 인식 및 교정했습니다."
            )
        except Exception as e:
            logger.error(f"Gemini OCR extraction error: {e}", exc_info=True)
            return AIMenuParseResponse(
                success=False,
                items=[],
                raw_response=str(e),
                message=f"Gemini 이미지 메뉴 분석 중 오류 발생: {str(e)}"
            )

    @staticmethod
    async def extract_menu_from_text(raw_text: str, existing_menus: Optional[List[str]] = None) -> AIMenuParseResponse:
        """입력된 텍스트로부터 메뉴 목록 추출 및 오타 교정 수행"""
        if not settings.GEMINI_API_KEY:
            return AIMenuParseResponse(
                success=False,
                items=[],
                message="GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요."
            )

        try:
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL_NAME,
                generation_config={"max_output_tokens": min(settings.GEMINI_API_MAX_TOKENS, 8192)}
            )

            prompt_parts = [SYSTEM_INSTRUCTION]
            if existing_menus:
                prompt_parts.append(f"기존 등록 메뉴 리스트 참고: {', '.join(existing_menus)}")
            prompt_parts.append(f"입력된 원본 텍스트:\n{raw_text}\n\n위 텍스트에서 메뉴 목록을 정형화하고 오타를 교정하여 JSON 배열로 반환하세요.")

            response = model.generate_content(prompt_parts)
            resp_text = response.text or ""
            cleaned = clean_json_response(resp_text)
            items = parse_extracted_items(cleaned)

            return AIMenuParseResponse(
                success=True,
                items=items,
                raw_response=resp_text,
                message=f"{len(items)}개의 메뉴 항목을 정형화 및 오타 교정 완료했습니다."
            )
        except Exception as e:
            logger.error(f"Gemini text parsing error: {e}", exc_info=True)
            return AIMenuParseResponse(
                success=False,
                items=[],
                raw_response=str(e),
                message=f"Gemini 텍스트 메뉴 분석 중 오류 발생: {str(e)}"
            )
