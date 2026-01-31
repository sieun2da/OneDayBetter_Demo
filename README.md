🚀 How to Run (Local)

이 프로젝트는 FastAPI 백엔드와 Streamlit 프론트엔드로 구성되어 있습니다.
아래 단계에 따라 로컬 환경에서 바로 실행할 수 있습니다.
---
1️⃣ Install dependencies

먼저 필요한 Python 패키지를 설치합니다.

pip install -r requirements.txt


Python 3.10 이상을 권장합니다.
---

2️⃣ Set environment variables

Upstage API 키는 환경 변수로 관리합니다.

cp .env.example .env


그 다음 .env 파일을 열어 아래 값을 설정해주세요.

UPSTAGE_API_KEY=your_upstage_api_key_here
TIMEZONE=Asia/Seoul


⚠️ .env 파일은 Git에 포함되지 않으며, 개인 API 키는 절대 공유하지 마세요.
---

3️⃣ Run backend (FastAPI)

처방전 처리 및 AI 파이프라인을 담당하는 백엔드를 실행합니다.

uvicorn app.main:app --reload
---


실행 후, 아래 주소에서 API 문서를 확인할 수 있습니다.

http://127.0.0.1:8000/docs

4️⃣ Run frontend (Streamlit)

사용자 인터페이스(UI)를 실행합니다.

streamlit run ui_app.py


브라우저가 자동으로 열리며,
처방전 업로드 → 결과 확인까지 바로 테스트할 수 있습니다.
---

✅ What happens next?

처방전 업로드

Document Parse → Extraction → Solar 검증

복약 알림 + 생활 케어 메시지 자동 생성

개인 일정에 맞춘 알림 타임라인 확인

Fine-tuning 없이, RAG 없이,
오직 Upstage API만으로 구현된 데모 파이프라인입니다.