
VALIDATE_SYSTEM = """You are a validation assistant for prescription extraction.
Use ONLY the provided parsed prescription content as the source of truth.
Do not guess or hallucinate. If a value is not found, return an empty string.
"""

def validate_user_prompt(parsed_html: str, extracted_json: str) -> str:
    return f"""Parsed prescription (source of truth):

{parsed_html}

Extracted JSON (may contain mistakes):

{extracted_json}

Task:

Verify each medication’s instructions by locating the exact instruction text in the SAME ROW as drug_name in the parsed prescription.

If the current instructions is wrong, replace it with the correct one from that row.

Keep all other fields unchanged.

Output ONLY the corrected JSON with this schema:

{{
  "medications": [
    {{
      "drug_name": "string",
      "dose_per_time": "string",
      "times_per_day": "string",
      "total_days": "string",
      "instructions": "string"
    }}
  ]
}}
"""


PUSH_SYSTEM = """너는 의료 진단을 하지 않는 생활 케어 AI다.
사용자에게 보내는 "푸시 알림 문장"을 매우 짧게 생성한다.
진단/치료 판단 금지. 불안을 유발하는 표현 금지.
심리적인 안정감을 주도록 할 것.
"""

def push_user_prompt(validated_json_str: str) -> str:
    return f"""아래는 사용자가 현재 복용 중인 약 정보이다.

이 약 정보와 복약 상황을 바탕으로,
앱 푸시에 사용할 수 있는 "짧은 생활습관 및 컨디션 관리 알림 문장"을 생성해줘.

조건:
- 의료 진단, 병명 추정, 치료 판단은 하지 말 것
- 약 성분을 단정적으로 해석하지 말 것
- 생활습관 중심(수분 섭취, 휴식, 수면, 위생, 눈 피로 관리, 규칙적인 식사 등)
- 부담 없고 안심되는 톤
- 각 문장은 45자 이내
- 이모지는 문장당 최대 1개
- 같은 내용 반복 금지

출력 요구사항:
- 10:00에 보낼 행동습관 알림 1개
- 16:00에 보낼 행동습관 알림 1개
- 19:00에 보낼 행동습관 알림 1개
- 각 시간대마다 "희망/회복" 긍정 메시지 1개씩(각각 다르게, 25자 이내)
- 출력은 반드시 JSON만

출력 형식(JSON):
{{
  "habit_pushes": [
    {{"time": "10:00", "habit": "...", "positive": "..."}},
    {{"time": "16:00", "habit": "...", "positive": "..."}},
    {{"time": "19:00", "habit": "...", "positive": "..."}}
  ]
}}

복용 중인 약 정보(JSON):
```json
{validated_json_str}
"""