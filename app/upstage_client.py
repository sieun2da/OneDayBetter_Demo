import os
import json
import base64
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
API_KEY = os.getenv("UPSTAGE_API_KEY")

# ---------------------------
# 1) Document Parse (requests)
#    Playground 설정 반영:
#    - model: document-parse-260128
#    - mode: enhanced
#    - ocr: auto
#    - output_formats: html
#    - base64_encoding: ['figure']
# ---------------------------

def document_parse(file_path: str) -> dict:
    """
    Upstage Document Parsing API
    file_path: pdf/jpg/png 등 업로드된 파일 경로
    returns: response JSON dict
    """
    if not API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY not set")

    url = "https://api.upstage.ai/v1/document-digitization"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    data = {
        "model": "document-parse-260128",
        "mode": "enhanced",
        "ocr": "auto",
        "output_formats": "html",
        "base64_encoding": "['figure']"
    }

    with open(file_path, "rb") as f:
        files = {
            "document": (
                os.path.basename(file_path),
                f,
                "application/octet-stream"
            )
        }
        resp = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=120
        )

    if not resp.ok:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise RuntimeError(f"Document Parse failed: {resp.status_code} {err}")

    return resp.json()


def extract_html_from_docparse(resp_json: dict) -> str:

    for k in ["content", "html", "text", "result"]:
        v = resp_json.get(k)
        if isinstance(v, str) and v.strip():
            return v


    def find_str(o):
        if isinstance(o, dict):
            for kk, vv in o.items():
                if kk in ("html", "content", "text") and isinstance(vv, str) and vv.strip():
                    return vv
                got = find_str(vv)
                if got:
                    return got
        elif isinstance(o, list):
            for item in o:
                got = find_str(item)
                if got:
                    return got
        return ""

    return find_str(resp_json) or ""


# ---------------------------
# 2) Universal Extraction (OpenAI SDK style)
#    base_url: /v1/information-extraction
#    model: information-extract
# ---------------------------

def _file_to_base64(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def universal_extract(file_path: str, json_schema: dict) -> dict:
    """
    Upstage Universal Extraction (Information Extraction)
    file_path: pdf/jpg/png 파일 경로
    json_schema: response_format json_schema에 넣을 schema(dict)
    returns: extracted json object(dict)
    """
    if not API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY not set")

    client = OpenAI(
        api_key=API_KEY,
        base_url="https://api.upstage.ai/v1/information-extraction"
    )

    b64 = _file_to_base64(file_path)

    resp = client.chat.completions.create(
        model="information-extract",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:application/octet-stream;base64,{b64}"
                        }
                    }
                ]
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "prescription_schema",
                "schema": json_schema
            }
        }
    )

    content = resp.choices[0].message.content
    return json.loads(content)


# ---------------------------
# 3) Solar Chat (OpenAI SDK style)
#    base_url: /v1
#    model: solar-pro3
# ---------------------------

def solar_chat(system: str, user: str, model: str = "solar-pro3") -> str:
    """
    Solar LLM 호출 (검증/푸시문구 생성에 사용)
    returns: message content (string)
    """
    if not API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY not set")

    client = OpenAI(
        api_key=API_KEY,
        base_url="https://api.upstage.ai/v1"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0
    )
    return resp.choices[0].message.content
