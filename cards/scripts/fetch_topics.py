# -*- coding: utf-8 -*-
"""从 kfhot 拉选题候选（方式 B：自动选题）

用法:
  python fetch_topics.py                       # 默认 5 个候选
  python fetch_topics.py --count 5 --days 7
  python fetch_topics.py --topic 筋膜刀
  python fetch_topics.py --json                # 输出原始 JSON（给 agent 读）

依赖: 项目内 .claude/skills/kfinfo/scripts/kfinfo.py
环境: KFHOT_BASE_URL（默认 https://kfhot.jianhengyiliao.com，旧的 IP:8000 已下线）
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]           # wxAuto/
KFINFO = ROOT / ".claude" / "skills" / "kfinfo" / "scripts" / "kfinfo.py"
BASE = os.environ.get("KFHOT_BASE_URL", "https://kfhot.jianhengyiliao.com").rstrip("/")


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main():
    count = arg("--count", "5")
    days = arg("--days", "7")
    topic = arg("--topic")
    as_json = "--json" in sys.argv

    if not KFINFO.exists():
        raise SystemExit("找不到 kfinfo 脚本: %s" % KFINFO)

    cmd = [sys.executable, str(KFINFO), "pick", "--count", count, "--days", days]
    if topic:
        cmd += ["--topic", topic]

    env = dict(os.environ)
    env["KFHOT_BASE_URL"] = BASE
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if proc.returncode != 0:
        raise SystemExit("kfinfo 调用失败:\n" + (proc.stderr or "")[-800:])

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise SystemExit("kfinfo 返回的不是 JSON:\n" + proc.stdout[:500])

    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    picks = data.get("picks") or []
    print(f"kfhot 选题候选（{data.get('date')} · 近 {data.get('days')} 天 · 共 {len(picks)} 个）\n")
    for i, p in enumerate(picks, 1):
        print(f"[{i}] {p.get('topic')}")
        print(f"    方向: {p.get('direction')}")
        print(f"    来源: {p.get('source')}")
        print(f"    链接: {p.get('url')}")
        n = len(p.get("items") or [])
        print(f"    素材: {n} 条")
        for it in (p.get("items") or [])[:3]:
            t = (it.get("title") or "").strip()
            print(f"      · {t[:60]}")
        print()

    print("选定后：把该候选的 items 交给 agent 展开成 deck.json，再跑 validate_deck.py + build_cards.py")
    print(f"（数据取自 kfhot 平台，截止最近一次抓取）")


if __name__ == "__main__":
    main()
