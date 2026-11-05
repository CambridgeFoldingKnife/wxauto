# -*- coding: utf-8 -*-
"""查询上次已提交的任务，摸清 CVSync2AsyncGetResult 的响应结构。"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "baoyu-cover-image" / "scripts"))

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

env = {}
for line in (ROOT / ".baoyu-skills" / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

from backends.backend_jimeng import JimengBackend  # noqa: E402

task_id = sys.argv[1] if len(sys.argv) > 1 else "145069106045712610"
b = JimengBackend(env["JIMENG_ACCESS_KEY_ID"], env["JIMENG_SECRET_ACCESS_KEY"])
raw = b._make_request(b.ACTION_QUERY, {"task_id": task_id, "req_key": b.REQ_KEY})
print("查询动作:", b.ACTION_QUERY, "| task_id:", task_id)
print("RAW:", json.dumps(raw, ensure_ascii=False, indent=2))
sys.exit(0)