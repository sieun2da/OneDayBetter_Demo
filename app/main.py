import os, json
from fastapi import FastAPI, UploadFile, File, HTTPException
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.storage import new_run_dir, save_text, save_json
from app.scheduler import start_scheduler, store

from app.upstage_client import (
    document_parse,
    extract_html_from_docparse,
    universal_extract,
    solar_chat
)
from app.prompts import (
    VALIDATE_SYSTEM,
    validate_user_prompt,
    PUSH_SYSTEM,
    push_user_prompt
)
from app.instruction_parser import build_med_schedules

load_dotenv()
TZ = os.getenv("TIMEZONE", "Asia/Seoul")

app = FastAPI(title="Upstage Prescription AI Agent (Prototype)")

@app.on_event("startup")
def _startup():
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data/runs", exist_ok=True)
    start_scheduler(tz=TZ)
    print("[SCHEDULER] started")


def future_at(hhmm: str, tz: str) -> str:
    """
    오늘 HH:MM. 이미 지난 시간이면 내일로 이월.
    """
    now = datetime.now(ZoneInfo(tz))
    h, m = map(int, hhmm.split(":"))
    dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if dt <= now:
        dt = dt + timedelta(days=1)
    return dt.isoformat()


@app.post("/run")
async def run_agent(
    pdf: UploadFile = File(...),
    breakfast: str = "08:00",
    lunch: str = "12:30",
    dinner: str = "19:00",
    wake: str = "08:00",
    sleep: str = "22:00",
):
    run_id, run_path = new_run_dir()

    try:
        print(f"[RUN:{run_id}] start")

  
        file_bytes = await pdf.read()
        filename = pdf.filename or f"{run_id}.bin"
        file_path = os.path.join("data", "uploads", filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        print(f"[RUN:{run_id}] saved file -> {file_path} ({len(file_bytes)} bytes)")

 
        print(f"[RUN:{run_id}] calling document_parse...")
        docparse_json = document_parse(file_path)
        save_json(run_path, "docparse_response.json", docparse_json)

        html = extract_html_from_docparse(docparse_json)
        save_text(run_path, "docparse.html", html)
        print(f"[RUN:{run_id}] docparse saved -> {os.path.join(run_path, 'docparse.html')} (len={len(html)})")

      
        print(f"[RUN:{run_id}] calling universal_extract...")
        prescription_schema = {
            "type": "object",
            "properties": {
                "medications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string"},
                            "dose_per_time": {"type": "string"},
                            "times_per_day": {"type": "string"},
                            "total_days": {"type": "string"},
                            "instructions": {"type": "string"}
                        },
                        "required": [
                            "drug_name",
                            "dose_per_time",
                            "times_per_day",
                            "total_days",
                            "instructions"
                        ]
                    }
                }
            },
            "required": ["medications"]
        }

        ie_json = universal_extract(file_path, prescription_schema)
        save_json(run_path, "ie.json", ie_json)
        print(f"[RUN:{run_id}] ie saved -> {os.path.join(run_path, 'ie.json')}")

    
        print(f"[RUN:{run_id}] calling solar validate...")
        validate_user = validate_user_prompt(html, json.dumps(ie_json, ensure_ascii=False))
        corrected_str = solar_chat(VALIDATE_SYSTEM, validate_user, model="solar-pro3")

        corrected_json = json.loads(corrected_str)
        save_json(run_path, "validated.json", corrected_json)
        print(f"[RUN:{run_id}] validated saved -> {os.path.join(run_path, 'validated.json')}")

       
        print(f"[RUN:{run_id}] calling solar push...")
        push_user = push_user_prompt(json.dumps(corrected_json, ensure_ascii=False))
        push_str = solar_chat(PUSH_SYSTEM, push_user, model="solar-pro3")

        push_json = json.loads(push_str)
        save_json(run_path, "push.json", push_json)
        print(f"[RUN:{run_id}] push saved -> {os.path.join(run_path, 'push.json')}")

       
        meal_times = {"breakfast": breakfast, "lunch": lunch, "dinner": dinner}
        wake_sleep = {"wake": wake, "sleep": sleep}

   
        med_schedules = build_med_schedules(corrected_json, meal_times, wake_sleep, tz=TZ)

      
        habit_pushes = push_json.get("habit_pushes", [])

     
        defaults = [
            {"time": "10:00", "habit": "물 한 잔으로 컨디션을 챙겨요 💧", "positive": "오늘도 충분히 잘하고 있어요."},
            {"time": "16:00", "habit": "잠깐 눈 쉬고 어깨도 풀어줘요 🌿", "positive": "작은 휴식이 큰 힘이 돼요."},
            {"time": "19:00", "habit": "저녁엔 화면 줄이고 편히 쉬어요 😊", "positive": "회복은 천천히 와도 괜찮아요."},
        ]
        while len(habit_pushes) < 3:
            habit_pushes.append(defaults[len(habit_pushes)])

        fixed_times = ["10:00", "16:00", "19:00"]
        habit_schedules = []
        for i, t in enumerate(fixed_times):
            h = habit_pushes[i]
            habit = (h.get("habit") or "").strip()
            pos = (h.get("positive") or "").strip()
            msg = f"{habit} {pos}".strip()

            habit_schedules.append({
                "fire_at": future_at(t, TZ),
                "type": "HABIT",
                "message": msg,
                "meta": {"kind": f"habit_{t.replace(':','')}"}
            })

        schedules_all = med_schedules + habit_schedules
        schedules_due = [s for s in schedules_all if s.get("fire_at")]

        save_json(run_path, "schedules.json", schedules_all)
        store.add_many(schedules_due)

        print(f"[RUN:{run_id}] schedules saved -> {os.path.join(run_path, 'schedules.json')}")
        print(f"[RUN:{run_id}] schedules added to scheduler -> {len(schedules_due)}")

        return {
            "run_id": run_id,
            "artifacts_dir": run_path,
            "meal_times": meal_times,
            "wake_sleep": wake_sleep,
            "medications_count": len(corrected_json.get("medications", [])),
            "scheduled_count": len(schedules_due),
            "note": "DP + IE + Solar(validate/push) + schedules (times/day & days considered + after-meal number in message)"
        }

    except Exception as e:
        print(f"[RUN:{run_id}] ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
