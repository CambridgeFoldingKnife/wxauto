# -*- coding: utf-8 -*-
"""
健衡学园 · 每日批量计划器（Agent 无关 / 可移植核心）
--------------------------------------------------------------
纯 Python、零依赖、任何 AI 代理或定时器都可调用。

职责（不含写作/生图/推送，那些由执行方按任务单做）：
  plan       读 accounts/*.json + accounts/.schedule.json，
             算出"今天该发哪些号 + 从选题池轮换取主题"，写 tasks/today.json 任务单
  mark       执行完成后回写 schedules.（更新 上次发文 / 选题指针）

用法:
  python daily-batch.py --plan                # 生成今日任务单并打印
  python daily-batch.py --mark                # 标记今日任务已完成（按 task 里 date)
  python daily-batch.py --status              # 查看各号状态
  python daily-batch.py --date 2026-09-12     # 指定日期（默认今天）
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ACCOUNTS_DIR = ROOT / "accounts"
SCHEDULE_FILE = ACCOUNTS_DIR / ".schedule.json"
TASKS_DIR = ROOT / "tasks"
STYLE_GUIDE = ROOT / ".claude" / "skills" / "wx-auto-publish" / "references" / "style-guide.md"
IMAGE_STYLE_LOCK = ROOT / ".claude" / "skills" / "wx-auto-publish" / "references" / "image-style-lock.md"

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_schedule() -> dict:
    if SCHEDULE_FILE.exists():
        try:
            return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {}


def save_schedule(s: dict) -> None:
    SCHEDULE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def load_accounts() -> list[dict]:
    accounts = []
    for f in sorted(ACCOUNTS_DIR.glob("*.json")):
        if f.name == ".schedule.json":
            continue
        try:
            accounts.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  账号文件解析失败 {f.name}: {e}", file=sys.stderr)
    return accounts


def cadence_due(acct: dict, date: datetime.date, state: dict) -> bool:
    """按 cadence 判断 date 该不该发。"""
    cad = acct.get("cadence") or {}
    if cad.get("daily"):
        return True
    if cad.get("weekdays"):
        wd = []  # 1=Mon … 7=Sun
        base, extra = divmod(date.weekday() + 1, 7)
        return (date.weekday() + 1) in cad["weekdays"]
    n = cad.get("every_n_days")
    if n:
        last = state.get("上次发文")
        if not last:
            return True
        try:
            last_d = datetime.date.fromisoformat(last)
        except ValueError:
            return True
        return (date - last_d).days >= n
    return False


def next_topic(acct: dict, state: dict) -> tuple[str, str]:
    pool = (acct.get("outline") or {}).get("选题池") or []
    if not pool:
        return ("", "")
    ptr = int(state.get("选题指针", 0)) % len(pool)
    item = pool[ptr]
    return item.get("主题", ""), item.get("方向", "")


def plan(date: datetime.date) -> list[dict]:
    schedule = load_schedule()
    tasks = []
    for acct in load_accounts():
        alias = acct["alias"]
        st = schedule.get(alias, {})
        if not cadence_due(acct, date, st):
            continue
        topic, direction = next_topic(acct, st)
        slug = f"{date.isoformat()}-{alias}-{''.join(c for c in topic if c.isalnum())[:10] or 'topic'}"
        tasks.append({
            "date": date.isoformat(),
            "alias": alias,
            "name": acct.get("name", alias),
            "topic": topic,
            "direction": direction,
            "theme": acct.get("theme", "jianheng"),
            "author": acct.get("author", ""),
            "image_style": acct.get("image_style", ""),
            "outline_file": str(ACCOUNTS_DIR / f"{alias}.json"),
            "style_guide": str(STYLE_GUIDE),
            "image_style_lock": str(IMAGE_STYLE_LOCK),
            "out_dir": f"drafts/{slug}",
        })
    return tasks


def main() -> None:
    ap = argparse.ArgumentParser(description="每日批量计划器")
    ap.add_argument("--plan", action="store_true", help="生成今日任务单")
    ap.add_argument("--mark", action="store_true", help="把今日任务标记为已完成（轮换选题指针）")
    ap.add_argument("--status", action="store_true", help="查看各号状态")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()

    date = datetime.date.fromisoformat(args.date)
    schedule = load_schedule()

    if args.status:
        for acct in load_accounts():
            st = schedule.get(acct["alias"], {})
            print(f"- {acct['name']} [{acct['alias']}] 上次发文={st.get('上次发文','-')} 选题指针={st.get('选题指针',0)}")
        sys.exit(0)

    if args.plan:
        tasks = plan(date)
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        (TASKS_DIR / "today.json").write_text(
            json.dumps({"date": date.isoformat(), "tasks": tasks}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(json.dumps({"date": date.isoformat(), "task_count": len(tasks), "tasks": tasks},
                         ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.mark:
        tf = TASKS_DIR / "today.json"
        if not tf.exists():
            print("错误: 没有 tasks/today.json，先跑 --plan", file=sys.stderr)
            sys.exit(1)
        data = json.loads(tf.read_text(encoding="utf-8"))
        for t in data.get("tasks", []):
            alias = t["alias"]
            st = schedule.setdefault(alias, {})
            st["上次发文"] = date.isoformat()
            st["选题指针"] = int(st.get("选题指针", 0)) + 1
        save_schedule(schedule)
        print(json.dumps({"ok": True, "marked": date.isoformat()}, ensure_ascii=False))
        sys.exit(0)

    ap.print_help()


if __name__ == "__main__":
    main()