from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import json

from app.services.gemini_service import GeminiService
from app.schemas.ai_schema import TextMenuParseRequest, AIMenuParseResponse

router = APIRouter(prefix="/api/ai", tags=["AI Menu Extraction"])

@router.post("/ocr-menu", response_model=AIMenuParseResponse)
async def ocr_menu(
    image_file: UploadFile = File(...),
    existing_menus: Optional[str] = Form(None)  # JSON 문자열 리스트
):
    """
    카페 메뉴판 이미지를 업로드받아 Gemini 멀티모달 Vision API를 통해
    메뉴 목록을 OCR 인식하고 오탈자를 교정하여 정형화된 JSON으로 반환합니다.
    """
    if not image_file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")

    contents = await image_file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB 제한
        raise HTTPException(status_code=400, detail="이미지 파일 크기는 최대 10MB까지 가능합니다.")

    existing_list = []
    if existing_menus:
        try:
            existing_list = json.loads(existing_menus)
        except Exception:
            existing_list = [m.strip() for m in existing_menus.split(",") if m.strip()]

    result = await GeminiService.extract_menu_from_image(contents, existing_list)
    return result

@router.post("/text-menu", response_model=AIMenuParseResponse)
async def text_menu(payload: TextMenuParseRequest):
    """
    입력된 텍스트에서 메뉴 목록을 추출하고 Gemini LLM을 통해 오탈자를 교정하여 반환합니다.
    """
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="텍스트를 입력해야 합니다.")

    result = await GeminiService.extract_menu_from_text(payload.raw_text, payload.existing_menus)
    return result
