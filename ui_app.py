import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from textwrap import dedent

import requests
import streamlit as st
import streamlit.components.v1 as components

API_URL = "http://127.0.0.1:8000/run"
TZ = "Asia/Seoul"

st.set_page_config(page_title="Upstage Prescription Agent", layout="centered")


st.markdown(dedent("""
<style>
:root{
  --blue:#3182F6;
  --text:#111827;
  --muted:rgba(17,24,39,0.60);
  --border:rgba(17,24,39,0.08);
  --bg:#F7F8FA;
  --card:#FFFFFF;
  --soft:rgba(49,130,246,0.08);
}

html, body, [class*="css"] {
  font-family: Pretendard, Apple SD Gothic Neo, Noto Sans KR, system-ui, -apple-system;
}

body { background: var(--bg); }


.block-container {
  padding-top: 2.6rem;
  max-width: 880px;
}

.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 14px;
  box-shadow: 0 10px 28px rgba(0,0,0,0.04);
}

.card:first-of-type{
  margin-top: 8px;
}

.topline{
  height: 4px;
  background: linear-gradient(90deg, var(--blue), rgba(49,130,246,0.15));
  border-radius: 999px;
  margin-bottom: 14px;
}

.small { color: var(--muted); font-size: 0.95rem; line-height: 1.45; }

.badges{ display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
.badge{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.85rem;
  background: rgba(49,130,246,0.10);
  color: var(--blue);
  border: 1px solid rgba(49,130,246,0.18);
}

.arch{
  border-left: 4px solid var(--blue);
  padding-left: 12px;
  margin-top: 8px;
}
.arch-step{
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #fff;
  margin: 10px 0;
}
.arch-title{
  font-weight: 900;
  color: var(--text);
  margin-bottom: 4px;
}
.arch-desc{
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.45;
}
.highlight{
  background: var(--soft);
  border: 1px solid rgba(49,130,246,0.16);
  border-radius: 14px;
  padding: 12px 12px;
  margin-top: 10px;
}


div.stButton > button{
  background: var(--blue) !important;
  color: white !important;
  border: none !important;
  border-radius: 14px !important;
  font-weight: 800 !important;
  padding: 0.75rem 1rem !important;
}
div.stButton > button:disabled{
  opacity: 0.45;
}

div[data-baseweb="input"] input { border-radius: 12px !important; }
div[data-testid="stFileUploaderDropzone"] {
  border-radius: 16px;
  border: 1px dashed rgba(49,130,246,0.35);
}

hr { border: none; height: 1px; background: var(--border); margin: 14px 0; }
</style>
"""), unsafe_allow_html=True)

# ----------------------------
# Header
# ----------------------------
st.markdown(dedent("""
<div class="card">
  <div class="topline"></div>
  <div style="font-size:1.45rem; font-weight:900; color:var(--text);">
    💊 처방전 AI Agent
  </div>
  <div class="small" style="margin-top:6px;">
    <b>Fine-tuning 없이</b>, <b>RAG 없이</b>, <b>오직 Upstage API</b>만으로<br/>
처방전 문서를 <b>구조화</b>하고 Solar로 <b>검증</b>해,
복약 알림과 생활 케어까지 자연스럽게 연결하는 서비스입니다.<br/>
<br/>
이 데모 버전은
Upstage 모델만으로,<br/> 우리가 상상한 것들을 구현할 수 있다는 것을 증명하는 기획 단계 결과물입니다.
  </div>
  <div class="badges">
    <span class="badge">Only Upstage</span>
    <span class="badge">No Fine-tuning</span>
    <span class="badge">No RAG</span>
  </div>

  <div class="highlight small">
    💙 이 서비스는 “진단/치료 판단”을 하지 않습니다.  
    대신 <b>복약 루틴</b>과 <b>생활 습관</b>을 꾸준히 이어가도록 도와,
    사용자가 부담 없이 회복 루틴을 유지하게 합니다.
  </div>
</div>
"""), unsafe_allow_html=True)

# ----------------------------
# Architecture (detailed) 
# ----------------------------
arch_html = dedent("""
<div class="card">
  <div style="font-weight:900; font-size:1.05rem;">아키텍처</div>

  <div class="arch">

    <div class="arch-step">
      <div class="arch-title">1) 처방전 입력</div>
      <div class="arch-desc">
        사용자가 처방전(PDF/JPG/PNG)을 업로드합니다.
      </div>
    </div>

    <div class="arch-step">
      <div class="arch-title">2) Document Parse API → “문서 구조(HTML)”</div>
      <div class="arch-desc">
        처방전의 표/행/텍스트 구조를 유지한 <b>HTML</b>을 생성합니다.  
        (약 이름이 어떤 행에 있고, 지시문이 같은 행에 붙어있는지까지 보존)
      </div>
    </div>

    <div class="arch-step">
      <div class="arch-title">3) Information Extraction API → “핵심 데이터(JSON)”</div>
      <div class="arch-desc">
        약명 / 투여량 / 1일 횟수 / 투약일수 / 복약 지시문을 <b>JSON</b>으로 추출합니다.
      </div>
    </div>

    <div class="arch-step">
      <div class="arch-title">4) Solar LLM 검증 → “HTML ↔ JSON 교차 검수”</div>
      <div class="arch-desc">
        Solar가 <b>HTML의 같은 행(row)</b>에서 지시문을 다시 찾아,
        Extraction 결과(JSON)의 instructions를 <b>근거 기반으로 교정</b>합니다.  
        (추측/환각 없이, 문서에 없으면 빈 값)
      </div>
    </div>

    <div class="arch-step">
      <div class="arch-title">5) 스케줄 생성 → “사용자 생활시간에 맞춘 알림”</div>
      <div class="arch-desc">
        검증된 처방 JSON + 사용자의 식사/기상/취침 시간을 조합해
        복약 지시문(예: 식후30분)을 그대로 반영한 스케줄을 만듭니다.
      </div>
    </div>

    <div class="arch-step">
      <div class="arch-title">6) Solar LLM 케어 → “생활 습관 + 긍정 메시지”</div>
      <div class="arch-desc">
        Solar가 의료 판단 없이, 부담 없는 톤으로
        <b>수분/휴식/눈 피로/위생/수면</b> 등 생활 케어 푸시와  
        하루를 버틸 수 있는 <b>짧은 응원 메시지</b>를 함께 제공합니다.
      </div>
    </div>

  </div>

  <div class="highlight small">
    “회복은 방향이 맞으면, 시간은 따라옵니다.”  
    이 앱은 사용자의 하루에 <b>루틴을 자연스럽게 붙여</b> 꾸준히 이어가도록 돕습니다.
  </div>
</div>
""")


arch_iframe = f"""
<html>
<head>
<style>
:root{{
  --blue:#3182F6;
  --text:#111827;
  --muted:rgba(17,24,39,0.60);
  --border:rgba(17,24,39,0.08);
  --card:#FFFFFF;
  --soft:rgba(49,130,246,0.08);
}}
body{{ margin:0; padding:0; background:transparent; font-family:Pretendard, Apple SD Gothic Neo, Noto Sans KR, system-ui, -apple-system;}}
.card{{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 10px 28px rgba(0,0,0,0.04);
}}
.small {{ color: var(--muted); font-size: 0.95rem; line-height: 1.45; }}
.arch{{ border-left: 4px solid var(--blue); padding-left: 12px; margin-top: 8px; }}
.arch-step{{ padding: 10px 12px; border: 1px solid var(--border); border-radius: 14px; background: #fff; margin: 10px 0; }}
.arch-title{{ font-weight: 900; color: var(--text); margin-bottom: 4px; }}
.arch-desc{{ color: var(--muted); font-size: 0.92rem; line-height: 1.45; }}
.highlight{{ background: var(--soft); border: 1px solid rgba(49,130,246,0.16); border-radius: 14px; padding: 12px 12px; margin-top: 10px; }}
</style>
</head>
<body>
{arch_html}
</body>
</html>
"""

components.html(arch_iframe, height=520, scrolling=True)

# ----------------------------
# Input
# ----------------------------
st.subheader("입력")
st.markdown(dedent("""
<a href="https://drive.google.com/file/d/1969T2MwLNBlC3ybNz0wAiNv8cZJCzyz-/view?usp=sharing"
   target="_blank"
   style="
     display:inline-block;
     background: rgba(49,130,246,0.10);
     color: #3182F6;
     border: 1px solid rgba(49,130,246,0.22);
     padding: 10px 14px;
     border-radius: 14px;
     font-weight: 900;
     text-decoration: none;
     margin: 2px 0 10px 0;
   ">
  🗂️ 처방전 샘플
</a>
"""), unsafe_allow_html=True)
uploaded = st.file_uploader(
    "처방전 파일 업로드 (PDF / JPG / PNG)",
    type=["pdf", "jpg", "jpeg", "png"]
)

c1, c2, c3 = st.columns(3)
breakfast = c1.text_input("아침 식사", "08:00")
lunch = c2.text_input("점심 식사", "12:30")
dinner = c3.text_input("저녁 식사", "19:00")

c4, c5 = st.columns(2)
wake = c4.text_input("기상", "08:00")
sleep = c5.text_input("취침", "22:00")

st.markdown("---")

# ----------------------------
# Session state
# ----------------------------
for k, v in {
    "artifacts_dir": None,
    "run_id": None,
    "schedules": [],
    "push": None,
    "validated": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_artifacts(artifacts_dir: str):
    schedules = load_json(os.path.join(artifacts_dir, "schedules.json")) or []
    push = load_json(os.path.join(artifacts_dir, "push.json"))
    validated = load_json(os.path.join(artifacts_dir, "validated.json"))
    return schedules, push, validated


def parse_fire_at(item):
    s = item.get("fire_at")
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except:
        return None


# ----------------------------
# Run
# ----------------------------
run_btn = st.button("실행하기", disabled=(uploaded is None))

if run_btn and uploaded is not None:
    with st.spinner("처리 중..."):
        files = {"pdf": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
        params = {"breakfast": breakfast, "lunch": lunch, "dinner": dinner, "wake": wake, "sleep": sleep}

        r = requests.post(API_URL, files=files, params=params, timeout=600)
        r.raise_for_status()
        out = r.json()

        st.session_state.run_id = out.get("run_id")
        st.session_state.artifacts_dir = out.get("artifacts_dir")

        schedules, push, validated = load_artifacts(st.session_state.artifacts_dir)
        st.session_state.schedules = schedules
        st.session_state.push = push
        st.session_state.validated = validated

    st.success("완료!")

# ----------------------------
# Results
# ----------------------------
if st.session_state.artifacts_dir:
    st.markdown(dedent("""
<div class="card">
  <div style="font-weight:900; font-size:1.05rem;">결과</div>
  <div class="small" style="margin-top:6px;">
    아래 결과는 <b>Document Parse(HTML)</b>와 <b>Extraction(JSON)</b>을 Solar가 교차 검증한 뒤 생성됩니다.
  </div>
</div>
"""), unsafe_allow_html=True)

    st.write("Run ID:", st.session_state.run_id)
    st.code(st.session_state.artifacts_dir)

    colA, colB = st.columns(2)

    with colA:
        st.markdown(dedent("<div class='card'><div style='font-weight:900;'>검증된 처방 JSON</div>"), unsafe_allow_html=True)
        if st.session_state.validated:
            st.json(st.session_state.validated)
        else:
            st.info("validated.json이 없어요.")
        st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown(dedent("<div class='card'><div style='font-weight:900;'>생활 케어 푸시</div>"), unsafe_allow_html=True)
        if st.session_state.push:
            st.json(st.session_state.push)
        else:
            st.info("push.json이 없어요.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(dedent("<div class='card'><div style='font-weight:900;'>알림 타임라인</div>"), unsafe_allow_html=True)

    schedules = st.session_state.schedules or []
    parsed = []
    for s in schedules:
        dt = parse_fire_at(s)
        if dt:
            parsed.append((dt, s))
    parsed.sort(key=lambda x: x[0])

    if not parsed:
        st.warning("fire_at이 있는 스케줄이 없어요.")
    else:
        now = datetime.now(ZoneInfo(TZ))
        rows = []
        for dt, s in parsed:
            diff_min = int((dt - now).total_seconds() // 60)
            rows.append({
                "time": dt.strftime("%Y-%m-%d %H:%M"),
                "in(min)": diff_min,
                "type": s.get("type"),
                "message": s.get("message"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("처방전을 업로드하고 실행하기를 누르면 결과가 표시됩니다.")
