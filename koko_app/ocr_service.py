import base64
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


def ocr_passport(api_key, img_bytes):
    last_raw_text = [""]

    try:
        enhanced = enhance_passport_image(img_bytes)
        result = _call_pipe_llm(api_key, enhanced, PASSPORT_OCR_PROMPT, last_raw_text)
        if result.get("passport_number"):
            return normalize_passport_fields(result)
    except Exception as exc:
        result = {"error": f"API 调用失败: {exc}"}

    try:
        result2 = _call_pipe_llm(api_key, img_bytes, PASSPORT_OCR_PROMPT, last_raw_text)
        if result2.get("passport_number"):
            return normalize_passport_fields(result2)
        for key, value in result2.items():
            if isinstance(value, str) and re.match(r"^[A-Z]{1,2}[0-9]{6,8}$", value.strip()):
                result2["passport_number"] = value.strip()
                return normalize_passport_fields(result2)
        result2["error"] = f"OCR 未识别出护照号 | 原始响应: {last_raw_text[0][:400]}"
        return result2
    except Exception as exc:
        return {"error": f"API 调用失败(原图重试): {exc} | 原始响应: {last_raw_text[0][:200]}"}
