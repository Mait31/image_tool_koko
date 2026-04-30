import base64
import io
import json
import re

import anthropic

from .config import PIPELLM_BASE_URL, PIPELLM_MODEL
from .image_service import enhance_passport_image

PASSPORT_OCR_PROMPT = (
    "这是一张中国护照照片。请严格按下面的 JSON 结构返回结果，字段名必须完全一致，"
    "不要输出解释、不要输出 Markdown 代码块、不要补充多余文字。\n"
    "{"
    "\"passport_number\": \"护照号，例如 EM4419078\","
    "\"passport_type\": \"护照类型，例如 P\","
    "\"name\": \"姓名中文全名\","
    "\"last_name\": \"姓，例如 WANG\","
    "\"first_name\": \"名，例如 ZHIFENG\","
    "\"name_pinyin\": \"英文姓名全拼，例如 WANG ZHIFENG\","
    "\"birth_date\": \"出生日期，格式 YYYY-MM-DD\","
    "\"birth_place\": \"出生地点\","
    "\"issue_date\": \"签发日期，格式 YYYY-MM-DD\","
    "\"expiration_date\": \"有效期至，格式 YYYY-MM-DD\","
    "\"issue_place\": \"签发地点\","
    "\"issue_authority\": \"签发机关完整全称，例如中华人民共和国国家移民管理局或中华人民共和国公安部出入境管理局\","
    "\"gender\": \"性别，M 或 F\","
    "\"nationality\": \"国籍三字码，例如 CHN\","
    "\"country_code\": \"国家代码，例如 CHN\","
    "\"mrz_code1\": \"MRZ 第一行\","
    "\"mrz_code2\": \"MRZ 第二行\""
    "}"
)


def _call_pipe_llm(api_key, image_bytes, prompt, last_raw_text):
    b64 = base64.standard_b64encode(image_bytes).decode()
    client = anthropic.Anthropic(api_key=api_key, base_url=PIPELLM_BASE_URL)
    msg = client.messages.create(
        model=PIPELLM_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            }},
            {"type": "text", "text": prompt},
        ]}],
    )
    raw = msg.content[0].text.strip()
    last_raw_text[0] = raw
    text = raw
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def normalize_passport_fields(info):
    if not isinstance(info, dict):
        return info

    nat = (info.get("nationality") or "").strip()
    cc = (info.get("country_code") or "").strip()

    mrz2 = (info.get("mrz_code2") or "").strip()
    mrz_nat = ""
    if mrz2:
        clean = mrz2.replace(" ", "")
        if len(clean) >= 13:
            candidate = clean[10:13].replace("<", "").strip()
            if re.match(r"^[A-Z]{2,3}$", candidate):
                mrz_nat = candidate
        if not mrz_nat:
            match = re.search(r"(?<![A-Z])([A-Z]{3})(?=\d)", clean)
            if match:
                mrz_nat = match.group(1)

    def is_code(value):
        return bool(value and re.match(r"^[A-Z]{2,3}$", value))

    nat_map = {
        "中国": "CHN",
        "中华人民共和国": "CHN",
        "中国公民": "CHN",
        "中国籍": "CHN",
        "CHINESE": "CHN",
        "CHINA": "CHN",
        "CHINESE MAINLAND": "CHN",
    }

    if is_code(mrz_nat):
        info["nationality"] = mrz_nat
        info["country_code"] = mrz_nat
    elif is_code(cc):
        info["nationality"] = cc
    elif nat.upper() in nat_map or nat in nat_map:
        info["nationality"] = nat_map.get(nat.upper(), nat_map.get(nat, nat))
        info["country_code"] = info["nationality"]
    elif is_code(nat):
        info["country_code"] = nat
    elif is_code(cc):
        info["nationality"] = cc

    auth = (info.get("issue_authority") or "").strip()
    if auth:
        lower = auth.lower()
        if "immigration" in lower or "移民管理" in auth:
            info["issue_authority"] = "中华人民共和国国家移民管理局"
        elif "公安部" in auth or "public security" in lower:
            info["issue_authority"] = "中华人民共和国公安部出入境管理局"

    return info


def _rotate_image_bytes(img_bytes, angle):
    if not angle:
        return img_bytes
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        rotated = img.rotate(angle, expand=True)
        out = io.BytesIO()
        rotated.save(out, format="JPEG", quality=92)
        return out.getvalue()
    except Exception:
        return img_bytes


def ocr_passport(api_key, img_bytes):
    best_result = None
    last_error = ""

    for angle in (0, 90, 270, 180):
        rotated_bytes = _rotate_image_bytes(img_bytes, angle)
        attempt_bytes_list = [rotated_bytes, enhance_passport_image(rotated_bytes)]

        if angle in (180, 270):
            attempt_bytes_list = [rotated_bytes]

        for attempt_idx, attempt_bytes in enumerate(attempt_bytes_list, start=1):
            last_raw_text = [""]
            try:
                result = _call_pipe_llm(api_key, attempt_bytes, PASSPORT_OCR_PROMPT, last_raw_text)
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, str) and re.match(r"^[A-Z]{1,2}[0-9]{6,8}$", value.strip()) and not result.get("passport_number"):
                            result["passport_number"] = value.strip()
                            break

                    normalized = normalize_passport_fields(result)
                    if normalized.get("passport_number") and normalized.get("name"):
                        return normalized
                    if normalized.get("passport_number") and best_result is None:
                        best_result = normalized
                    if normalized.get("name"):
                        return normalized
            except Exception as exc:
                last_error = f"角度 {angle} / 尝试 {attempt_idx} 失败: {exc} | 原始响应: {last_raw_text[0][:200]}"

    if best_result is not None:
        best_result["error"] = best_result.get("error") or "OCR 识别到了护照号，但未稳定识别出中文姓名"
        return best_result

    return {"error": last_error or "OCR 未识别出中文姓名"}
