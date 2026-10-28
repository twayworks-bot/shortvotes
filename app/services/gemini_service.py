import asyncio
import io
import json
import re
import logging
from typing import List, Optional, Any, Tuple
from PIL import Image, ImageOps
import google.generativeai as genai

from app.config import settings, reload_gemini_settings
from app.schemas.ai_schema import ExtractedMenuItem, AIMenuParseResponse

logger = logging.getLogger(__name__)


def configure_gemini() -> str:
    """
    .env 파일 및 시스템 환경변수로부터 최신 Gemini 설정을 로드하고 클라이언트를 구성합니다.
    """
    reload_gemini_settings()
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    else:
        logger.warning("GEMINI_API_KEY is not set in environment or .env file.")
    return settings.GEMINI_API_KEY


configure_gemini()

SYSTEM_INSTRUCTION = """당신은 대한민국 카페, 전통찻집, 베이커리 및 음식점의 메뉴판 OCR 인식 및 데이터 정제 전문가입니다.
사용자가 제공한 메뉴판 이미지 또는 텍스트에서 실제 판매 중인 모든 메뉴 항목을 누락 없이 정확하게 추출하고 정제해야 합니다.

[핵심 작업 지침]
1. 이미지 방향(Orientation) 및 레이아웃 파악:
   - 메뉴판 사진이 90도(좌/우) 또는 180도 회전되어 촬영되었거나 기울어져 있는 경우, 글자의 상하좌우 방향을 먼저 판별하여 정방향으로 보정한 뒤 읽으세요.
   - 가로쓰기, 세로쓰기, 다단(Multi-column) 구성, 메뉴명과 가격이 떨어져 있는 표 형태 등 모든 레이아웃을 끝까지 스캔하여 메뉴와 가격을 정확히 매칭하세요.

2. 모든 판매 메뉴의 완전 추출 (전통찻집·카페·손글씨 포함):
   - 일반 카페 메뉴(커피, 라떼, 에이드, 스무디, 티, 베이커리)뿐만 아니라 **전통찻집/한방찻집 메뉴**(대추차, 쌍화차, 유자차, 매실차, 오미자차, 생강차, 국화차, 모과차, 솔잎차, 칡차, 십전대보탕, 식혜, 단호박식혜, 수정과, 미숫가루, 한과/떡 등)를 모두 정확히 인식하세요.
   - 인쇄된 글씨뿐만 아니라 메뉴판의 가장자리, 하단, 우측 등에 **종이 테이프, 마스킹 테이프, 포스트잇, 스티커 등에 손글씨(펜/매직)로 추가 부착된 메뉴**(예: 테이프에 손글씨로 적힌 '식혜 (단호박) 6,000원')도 절대 빠뜨리지 말고 추출하세요.
   - 메뉴명 주변에 **도장(스탬프)이나 손글씨로 찍힌 온도/옵션 표시**(예: 붉은 글씨 '온', '냉', '[온/냉]')도 놓치지 말고 인식하세요.
   - 빛 반사, 그림자, 수정 테이프로 일부 글자가 가려져 있더라도 주변 문맥과 한국어 표준 메뉴명을 바탕으로 정확히 복원하세요.

3. 비메뉴 텍스트 및 효능·설명 문구 엄격 분리:
   - **제외 대상**: 매장 상호명/로고(예: '난다나 찻집'), 이용 조건 및 안내 문구(예: '1인 가능', '1인 1잔', '주문 및 정리는 셀프입니다', '[차를 드신 후 반납해 주세요]'), 원산지 표시, 전화번호 등은 메뉴가 아니므로 절대 포함하지 마세요.
   - **효능/효과 부연 설명 제거**: 전통찻집이나 카페 메뉴판에서 메뉴명 아래/옆에 작은 글씨로 적힌 효능·효과·성분 설명(예: '불면증', '피로회복/감기', '비타민/피부미용', '각종 해독작용', '비타민/간건강', '면역력 강화', '두통완화/혈액순환' 등)은 메뉴명에 넣지 말고 제거하여 **순수 메뉴명**만 추출하세요.
   - **핵심 옵션 및 주재료 보존**: 단, 메뉴의 맛/주재료를 나타내는 표기(예: '식혜 (단호박)')나 제공 온도 옵션(예: '[온/냉]' -> '(온/냉)', 붉은 도장 '온' -> '(온)', 'HOT/ICE')은 괄호 형태로 메뉴명에 깔끔하게 포함하세요 (예: '유자차 (온/냉)', '매실차 (온/냉)', '오미자차 (온/냉)', '생강차 (온)', '식혜 (단호박)').
   - 만약 동일 메뉴의 HOT/ICE 또는 사이즈별 가격이 서로 다르게 병기되어 있다면 각각 별도의 메뉴 항목으로 분리하고, 가격이 동일하면 하나의 항목에 '(온/냉)' 또는 '(HOT/ICE)'로 표기하세요.

4. 오탈자 교정 및 기존 메뉴 참조:
   - OCR 인식 불량이나 사용자의 오탈자(예: '아에리카노' -> '아메리카노', '카페라때' -> '카페라떼', '자몽허니블랙티이' -> '자몽허니블랙티', '쌍화차아' -> '쌍화차')를 대한민국 표준 메뉴 명칭으로 교정하세요.
   - '기존 등록 메뉴 리스트'가 함께 제공된 경우, 유사한 메뉴는 기존 메뉴의 표기 방식을 우선 존중하세요.

5. 가격(price) 파싱 규칙:
   - '6,000원', '7,000원', '4,500', '6천원', '4.5', '4.5k' 등 다양한 가격 표기를 대한민국 원화(KRW) 기준 **정수(integer)**(예: 6000, 7000, 4500)로 변환하세요.
   - 가격이 명시되지 않은 항목만 0으로 설정하세요.

6. 카테고리(category) 분류 규칙:
   - 메뉴 특성에 따라 다음 중 가장 적합한 카테고리를 부여하세요:
     * "전통차/티": 대추차, 쌍화차, 유자차, 매실차, 오미자차, 생강차, 국화차, 모과차, 한방차, 녹차, 홍차, 허브티 등
     * "논커피/음료": 식혜, 단호박식혜, 수정과, 미숫가루, 초코/녹차/고구마라떼, 스무디, 주스 등
     * "커피": 아메리카노, 에스프레소, 카페라떼, 바닐라라떼, 카푸치노, 콜드브루 등
     * "에이드/티": 레몬/자몽/청포도에이드, 아이스티, 블렌딩티 등
     * "디저트/베이커리": 떡, 한과, 약과, 케이크, 빵, 쿠키, 빙수 등
     * "기타": 그 외 분류가 모호한 메뉴

7. 출력 형식:
   - 반드시 부가 설명이나 마크다운 코드블록 없이 순수한 JSON 배열만 출력하세요.
   - 각 객체는 반드시 "name" (문자열), "price" (정수), "category" (문자열) 키를 가져야 합니다.

JSON 출력 예시:
[
  {"name": "대추차", "price": 6000, "category": "전통차/티"},
  {"name": "쌍화차", "price": 6000, "category": "전통차/티"},
  {"name": "유자차 (온/냉)", "price": 6000, "category": "전통차/티"},
  {"name": "생강차 (온)", "price": 6000, "category": "전통차/티"},
  {"name": "국화차", "price": 7000, "category": "전통차/티"},
  {"name": "식혜 (단호박)", "price": 6000, "category": "논커피/음료"},
  {"name": "아메리카노 (HOT)", "price": 4500, "category": "커피"}
]
"""


def preprocess_menu_image(image_bytes: bytes, max_dimension: int = 2560) -> Image.Image:
    """
    업로드된 메뉴판 이미지를 Gemini Vision OCR에 최적화된 RGB 이미지로 전처리합니다.
    - EXIF 회전 정보 자동 보정 (스마트폰 카메라 촬영본 대응)
    - RGBA/P/CMYK 등을 RGB로 안전하게 변환
    - 과도한 고해상도 이미지를 LANCZOS 리샘플링으로 최적화하여 인식 속도 및 안정성 향상
    - 미세 대비 보정(autocontrast)으로 흐릿한 손글씨/테이프 글씨 가독성 강화
    """
    image = Image.open(io.BytesIO(image_bytes))
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[3])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size
    if max(width, height) > max_dimension:
        scale = max_dimension / float(max(width, height))
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    try:
        image = ImageOps.autocontrast(image, cutoff=0.3)
    except Exception:
        pass

    return image


def parse_price(raw_price: Any) -> int:
    """다양한 형태의 가격 문자열/숫자를 원(KRW) 단위 정수로 안전하게 파싱"""
    if raw_price is None or isinstance(raw_price, bool):
        return 0
    if isinstance(raw_price, int):
        return max(0, raw_price)
    if isinstance(raw_price, float):
        if 0 < raw_price < 100:
            return int(round(raw_price * 1000))
        return max(0, int(round(raw_price)))

    s = str(raw_price).strip().lower().replace(",", "").replace(" ", "")
    if not s:
        return 0

    # '6천원', '4.5천', '4.5k', '4.5천원' 처리
    m_k = re.search(r"(\d+(?:\.\d+)?)\s*(?:천원?|k)", s)
    if m_k:
        return int(round(float(m_k.group(1)) * 1000))

    # 소수점 약어 표기 (예: '4.5', '6.0') 처리
    m_dec = re.fullmatch(r"(\d+\.\d+)원?", s)
    if m_dec:
        val = float(m_dec.group(1))
        if 0 < val < 100:
            return int(round(val * 1000))
        return int(round(val))

    # 일반 정수 추출 (예: '6000원', '6000')
    m_int = re.search(r"(\d+)", s)
    if m_int:
        val = int(m_int.group(1))
        if 0 < val < 100:
            return val * 1000
        return val

    return 0


def clean_json_response(raw_text: str) -> str:
    """
    마크다운 코드블록(```json ... ```)이나 부가 설명이 섞인 LLM 응답에서
    메뉴명 내부의 대괄호(예: '유자차 [온/냉]')와 충돌하지 않도록 순수 JSON 문자열을 추출합니다.
    """
    if not raw_text:
        return "[]"

    text = raw_text.strip()

    # 1. 마크다운 코드블록(```json ... ```) 내부 텍스트 우선 분리
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence_match:
        fenced_body = fence_match.group(1).strip()
        if fenced_body:
            text = fenced_body

    # 2. 전체 텍스트가 곧바로 유효한 JSON인 경우
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # 3. JSONDecoder.raw_decode를 이용해 문자열 내 대괄호('[온/냉]')에 영향받지 않고 최외곽 JSON 배열/객체 추출
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch in ("[", "{"):
            try:
                _, end_idx = decoder.raw_decode(text[idx:])
                return text[idx : idx + end_idx].strip()
            except Exception:
                continue

    return text


def parse_extracted_items(cleaned_text: str) -> List[ExtractedMenuItem]:
    """JSON 텍스트를 파싱하여 정제된 ExtractedMenuItem 리스트로 변환"""
    cleaned = clean_json_response(cleaned_text)
    data = json.loads(cleaned)

    # 만약 최상위가 dict인 경우 (예: {"items": [...]}) 내부 리스트 추출
    if isinstance(data, dict):
        for key in ("items", "menus", "menu_items", "data", "result", "list"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # 단일 메뉴 객체인 경우 리스트로 래핑
            if any(k in data for k in ("name", "menu", "menu_name", "메뉴명")):
                data = [data]
            else:
                data = []

    if not isinstance(data, list):
        return []

    items: List[ExtractedMenuItem] = []
    seen = set()

    for entry in data:
        if not isinstance(entry, dict):
            continue

        raw_name = (
            entry.get("name")
            or entry.get("menu_name")
            or entry.get("menu")
            or entry.get("메뉴명")
            or entry.get("title")
            or ""
        )
        name = re.sub(r"\s+", " ", str(raw_name)).strip()
        if not name:
            continue

        raw_price = (
            entry.get("price")
            if "price" in entry
            else entry.get("가격", entry.get("cost", 0))
        )
        price = parse_price(raw_price)

        raw_category = (
            entry.get("category")
            or entry.get("카테고리")
            or entry.get("type")
            or "기본"
        )
        category = str(raw_category).strip() or "기본"

        dedup_key = (name.lower(), price)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        items.append(ExtractedMenuItem(name=name, price=price, category=category))

    return items


def _get_candidate_models() -> List[str]:
    """
    .env 또는 환경변수에 설정된 GEMINI_MODEL_NAME을 1순위로 사용하고,
    장애/호환성 문제 시 안정적인 폴백 모델을 후보로 반환합니다.
    """
    primary = (settings.GEMINI_MODEL_NAME or "gemini-2.5-flash").strip()
    candidates = [primary]
    for fallback in ("gemini-2.5-flash", "gemini-2.0-flash"):
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def _build_generation_config() -> dict:
    """
    .env의 GEMINI_API_MAX_TOKENS 설정을 반영하여 JSON 응답 스키마 및 출력 토큰을 구성합니다.
    """
    configured_max = settings.GEMINI_API_MAX_TOKENS if settings.GEMINI_API_MAX_TOKENS > 0 else 65536
    max_output_tokens = min(configured_max, 65536)
    return {
        "temperature": 0.1,
        "response_mime_type": "application/json",
        "max_output_tokens": max_output_tokens,
    }


async def _generate_and_parse(
    model_name: str,
    prompt_parts: List[Any],
) -> Tuple[List[ExtractedMenuItem], str]:
    """
    지정된 Gemini 모델로 비동기(스레드 풀) 생성 요청을 수행하고 메뉴 리스트를 파싱합니다.
    """
    gen_config = _build_generation_config()
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config=gen_config,
        )
        response = await asyncio.to_thread(model.generate_content, prompt_parts)
    except Exception as first_err:
        # 일부 구형 모델에서 max_output_tokens(65536) 또는 response_mime_type 미지원 시 8192로 재시도
        logger.warning(f"Primary generation_config failed on {model_name} ({first_err}), retrying with fallback config.")
        fallback_config = {
            "temperature": 0.1,
            "max_output_tokens": min(gen_config["max_output_tokens"], 8192),
        }
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config=fallback_config,
        )
        response = await asyncio.to_thread(model.generate_content, prompt_parts)

    raw_text = ( getattr(response, "text", None) or "" ).strip()
    items = parse_extracted_items(raw_text)
    return items, raw_text


class GeminiService:
    @staticmethod
    async def extract_menu_from_image(
        image_bytes: bytes,
        existing_menus: Optional[List[str]] = None
    ) -> AIMenuParseResponse:
        """메뉴판 이미지로부터 OCR 및 메뉴 추출, 오타 교정 수행 (.env의 GEMINI 설정 활용)"""
        api_key = configure_gemini()
        if not api_key:
            return AIMenuParseResponse(
                success=False,
                items=[],
                message="GEMINI_API_KEY가 설정되지 않았습니다. .env 파일 또는 컨테이너 환경변수(GEMINI_API_KEY)를 확인해 주세요."
            )

        try:
            processed_image = preprocess_menu_image(image_bytes)
        except Exception as img_err:
            logger.error(f"Image preprocessing error: {img_err}", exc_info=True)
            return AIMenuParseResponse(
                success=False,
                items=[],
                raw_response=str(img_err),
                message=f"유효하지 않거나 손상된 이미지 파일입니다: {str(img_err)}"
            )

        existing_context = ""
        if existing_menus:
            existing_context = f"\n[기존 등록 메뉴 리스트 참고 (유사 명칭 오타 보정 기준)]: {', '.join(existing_menus)}\n"

        user_prompt = (
            "첨부된 메뉴판 이미지를 정밀하게 분석하여 판매 중인 모든 메뉴 목록을 추출해 주세요.\n"
            "- 이미지가 90도(좌/우) 또는 180도 회전되어 있거나 세로로 적혀 있다면, 글자 방향에 맞춰 바르게 읽으세요.\n"
            "- 인쇄된 메뉴(전통차, 커피, 음료, 디저트 등)뿐만 아니라 마스킹 테이프나 종이에 손글씨로 덧붙여진 메뉴(예: '식혜 (단호박) 6,000원'), 도장/손글씨 온도 표기(예: '[온/냉]', '온')까지 빠짐없이 인식하세요.\n"
            "- 가게 상호명, '1인 가능', '주문 및 정리는 셀프입니다' 등 안내 문구와 메뉴 아래의 효능/설명(예: '불면증', '피로회복/감기', '비타민/피부미용', '각종 해독작용', '면역력 강화', '두통완화/혈액순환' 등)은 메뉴명에서 제외하세요.\n"
            f"{existing_context}"
            '결과는 반드시 [{"name": "메뉴명", "price": 정수_가격, "category": "카테고리"}] 형식의 JSON 배열로만 반환하세요.'
        )

        last_error: Optional[Exception] = None
        last_raw_text: str = ""

        # 1차 시도: 후보 모델 순서대로 원본(전처리) 이미지 분석
        # 만약 0건이 추출되면 이미지를 시계방향 90도 회전(반시계 90도 누운 사진 정방향 복원)하여 재시도
        orientations = [
            ("original", processed_image),
            ("rotated_90_cw", processed_image.rotate(-90, expand=True)),
        ]

        for model_name in _get_candidate_models():
            for orient_label, img_variant in orientations:
                try:
                    items, raw_text = await _generate_and_parse(
                        model_name=model_name,
                        prompt_parts=[user_prompt, img_variant],
                    )
                    last_raw_text = raw_text
                    if items:
                        logger.info(
                            f"Gemini OCR succeeded with model={model_name}, orientation={orient_label}, count={len(items)}"
                        )
                        return AIMenuParseResponse(
                            success=True,
                            items=items,
                            raw_response=raw_text,
                            message=f"{len(items)}개의 메뉴 항목을 성공적으로 인식 및 교정했습니다."
                        )
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Gemini OCR attempt failed (model={model_name}, orientation={orient_label}): {e}"
                    )
                    # API 인증/쿼터 에러 등 모델 자체 오류면 다음 회전 대신 다음 모델로 이동
                    break

        if last_error and not last_raw_text:
            logger.error(f"Gemini OCR extraction error: {last_error}", exc_info=True)
            return AIMenuParseResponse(
                success=False,
                items=[],
                raw_response=str(last_error),
                message=f"Gemini 이미지 메뉴 분석 중 오류 발생: {str(last_error)}"
            )

        return AIMenuParseResponse(
            success=False,
            items=[],
            raw_response=last_raw_text,
            message="이미지에서 유효한 메뉴 항목을 인식하지 못했습니다. 메뉴 글자가 잘 보이도록 촬영되었는지 확인해 주세요."
        )

    @staticmethod
    async def extract_menu_from_text(
        raw_text: str,
        existing_menus: Optional[List[str]] = None
    ) -> AIMenuParseResponse:
        """입력된 텍스트로부터 메뉴 목록 추출 및 오타 교정 수행 (.env의 GEMINI 설정 활용)"""
        api_key = configure_gemini()
        if not api_key:
            return AIMenuParseResponse(
                success=False,
                items=[],
                message="GEMINI_API_KEY가 설정되지 않았습니다. .env 파일 또는 컨테이너 환경변수(GEMINI_API_KEY)를 확인해 주세요."
            )

        existing_context = ""
        if existing_menus:
            existing_context = f"\n[기존 등록 메뉴 리스트 참고]: {', '.join(existing_menus)}\n"

        user_prompt = (
            f"입력된 원본 메뉴 텍스트:\n{raw_text}\n"
            f"{existing_context}\n"
            "위 텍스트에서 안내 문구나 효능 설명을 제외한 실제 판매 메뉴 목록을 추출하고, "
            "오탈자를 표준 메뉴명으로 교정한 뒤 "
            '[{"name": "메뉴명", "price": 정수_가격, "category": "카테고리"}] 형식의 JSON 배열로 반환하세요.'
        )

        last_error: Optional[Exception] = None
        last_raw_text: str = ""

        for model_name in _get_candidate_models():
            try:
                items, resp_text = await _generate_and_parse(
                    model_name=model_name,
                    prompt_parts=[user_prompt],
                )
                last_raw_text = resp_text
                if items:
                    return AIMenuParseResponse(
                        success=True,
                        items=items,
                        raw_response=resp_text,
                        message=f"{len(items)}개의 메뉴 항목을 정형화 및 오타 교정 완료했습니다."
                    )
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini text parse attempt failed (model={model_name}): {e}")

        if last_error and not last_raw_text:
            logger.error(f"Gemini text parsing error: {last_error}", exc_info=True)
            return AIMenuParseResponse(
                success=False,
                items=[],
                raw_response=str(last_error),
                message=f"Gemini 텍스트 메뉴 분석 중 오류 발생: {str(last_error)}"
            )

        return AIMenuParseResponse(
            success=False,
            items=[],
            raw_response=last_raw_text,
            message="입력된 텍스트에서 유효한 메뉴 항목을 찾을 수 없습니다."
        )
