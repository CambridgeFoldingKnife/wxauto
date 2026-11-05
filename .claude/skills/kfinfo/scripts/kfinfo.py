# -*- coding: utf-8 -*-
"""
kfinfo · 康复资讯聚合平台(kfhot)查询客户端(纯标准库,零依赖)

作用:让任意 agent 用一条命令拿到康复领域最新/检索/选题/体检数据。
数据源:kfhot(公网 ECS),内容是"权威+次权威"双轨的最新康复资讯。

用法:
  python kfinfo.py hot      [--days 7] [--topic 脑卒中康复] [--tier 权威] [--limit 10]
  python kfinfo.py items    [--keyword stroke] [--topic X] [--lang en] [--tier 权威]
                           [--date_from 2026-09-01] [--page 1] [--page_size 20]
  python kfinfo.py item     --id 1
  python kfinfo.py featured [--tier 权威]
  python kfinfo.py daily
  python kfinfo.py pick     [--count 5] [--tier 次权威] [--days 7]
  python kfinfo.py secondary [--page_size 20]
  python kfinfo.py topics
  python kfinfo.py health

基础地址:环境变量 KFHOT_BASE_URL 可覆盖(默认 http://60.205.181.202:8000)
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

BASE = "http://60.205.181.202:8000"   # 可被环境变量 KFHOT_BASE_URL 覆盖
api = BASE + "/api/v1"


def _fetch(path: str, params: dict | None = None) -> dict:
    url = f"{api}/{path}"
    if params:
        q = {k: v for k, v in params.items() if v not in (None, "")}
        if q:
            url += "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _out(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description="kfinfo · kfhot 平台查询")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("hot", help="近N日热点榜")
    p.add_argument("--days", type=int, default=7); p.add_argument("--topic", default="")
    p.add_argument("--tier", default=""); p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("items", help="多条件检索")
    p.add_argument("--topic", default=""); p.add_argument("--keyword", default="")
    p.add_argument("--lang", default=""); p.add_argument("--tier", default="")
    p.add_argument("--date_from", default=""); p.add_argument("--date_to", default="")
    p.add_argument("--page", type=int, default=1); p.add_argument("--page_size", type=int, default=20)

    p = sub.add_parser("item", help="单条详情"); p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("featured", help="每日精选"); p.add_argument("--tier", default="")

    sub.add_parser("daily", help="行业日报聚合")

    p = sub.add_parser("pick", help="自动选题包")
    p.add_argument("--count", type=int, default=5); p.add_argument("--tier", default="")
    p.add_argument("--topic", default=""); p.add_argument("--days", type=int, default=7)

    p = sub.add_parser("secondary", help="次权威快捷口"); p.add_argument("--page_size", type=int, default=20)

    sub.add_parser("topics", help="六主题清单")
    sub.add_parser("health", help="数据体检")

    args = ap.parse_args()
    cmd = args.cmd

    try:
        if cmd == "hot":
            _out(_fetch("hot", {"days": args.days, "topic": args.topic, "tier": args.tier, "limit": args.limit}))
        elif cmd == "items":
            _out(_fetch("items", {"topic": args.topic, "keyword": args.keyword, "lang": args.lang,
                                  "tier": args.tier, "date_from": args.date_from, "date_to": args.date_to,
                                  "page": args.page, "page_size": args.page_size}))
        elif cmd == "item":
            _out(_fetch(f"item/{args.id}"))
        elif cmd == "featured":
            _out(_fetch("featured", {"tier": args.tier}))
        elif cmd == "daily":
            _out(_fetch("daily"))
        elif cmd == "pick":
            _out(_fetch("pick", {"count": args.count, "tier": args.tier, "topic": args.topic, "days": args.days}))
        elif cmd == "secondary":
            _out(_fetch("secondary", {"page_size": args.page_size}))
        elif cmd == "topics":
            _out(_fetch("topics"))
        elif cmd == "health":
            _out(_fetch("health"))
        return 0
    except urllib.error.HTTPError as e:
        print(f"[错误] HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[错误] {type(e).__name__}: {e}", file=sys.stderr)
        print("提示:确认平台在线(公网 http://60.205.181.202:8000)或设置 KFHOT_BASE_URL", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())