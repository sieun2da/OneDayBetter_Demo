from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from zoneinfo import ZoneInfo

class InMemoryScheduleStore:
    def __init__(self):
        self.items = []

    def add_many(self, schedules):
        for s in schedules:
            s["sent"] = False
            self.items.append(s)

    def due(self, tz="Asia/Seoul"):
        now = datetime.now(ZoneInfo(tz))
        due_items = []

        for it in self.items:
            if it.get("sent") or not it.get("fire_at"):
                continue

            fire_at = datetime.fromisoformat(it["fire_at"])

            
            if fire_at.tzinfo is None:
                fire_at = fire_at.replace(tzinfo=ZoneInfo(tz))

            if fire_at <= now:
                due_items.append(it)

        return due_items

    def mark_sent(self, it):
        it["sent"] = True
        it["sent_at"] = datetime.now().isoformat()

store = InMemoryScheduleStore()
scheduler = BackgroundScheduler()

def start_scheduler(tz="Asia/Seoul"):
    def tick():
        for it in store.due(tz=tz):
           
            print(f"[PUSH][{it['type']}] {it['message']}")
            store.mark_sent(it)

    scheduler.add_job(tick, "interval", seconds=5)
    scheduler.start()
