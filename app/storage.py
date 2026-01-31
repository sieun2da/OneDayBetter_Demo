import os, json, uuid

BASE = "data/runs"

def new_run_dir():
    run_id = str(uuid.uuid4())
    path = os.path.join(BASE, run_id)
    os.makedirs(path, exist_ok=True)
    return run_id, path

def save_text(path, name, content):
    with open(os.path.join(path, name), "w", encoding="utf-8") as f:
        f.write(content)

def save_json(path, name, obj):
    with open(os.path.join(path, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
