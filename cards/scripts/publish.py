# -*- coding: utf-8 -*-
"""把一期卡片推成公众号「图片消息（newspic）」草稿

用法:
  python publish.py deck-stroke.json              # 默认 dry-run，只打印将要发送的内容
  python publish.py deck-stroke.json --push       # 真正写入草稿箱
  python publish.py deck-stroke.json --account jianheng-xueyuan

为什么不用 baoyu-post-to-wechat 的 CLI：
  它的 newspic 必须把图片写进正文 HTML 才会被上传，结果描述里会重复出现这 9 张图。
  这里直连 cgi-bin/material/add_material + cgi-bin/draft/add，正文只放图注。

凭据：读取 <项目>/.baoyu-skills/.env 的 WECHAT_APP_ID / WECHAT_APP_SECRET（不打印明文）
"""
import json
import mimetypes
import os
import re
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]        # cards/
PROJECT = ROOT.parent                             # wxAuto/
ENV_FILE = PROJECT / ".baoyu-skills" / ".env"
OUT = ROOT / "out"

API = "https://api.weixin.qq.com/cgi-bin"


# ------------------------------------------------------------------ 凭据
def load_env(path):
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def credentials():
    env = load_env(ENV_FILE)
    appid = os.environ.get("WECHAT_APP_ID") or env.get("WECHAT_APP_ID")
    secret = os.environ.get("WECHAT_APP_SECRET") or env.get("WECHAT_APP_SECRET")
    if not appid or not secret:
        raise SystemExit("缺少微信凭据：请在 %s 配置 WECHAT_APP_ID / WECHAT_APP_SECRET" % ENV_FILE)
    return appid, secret


# ------------------------------------------------------------------ 图注
def build_caption(deck):
    cap = deck.get("caption") or {}
    parts = []
    if cap.get("dataSource"):
        parts.append(f"数据来源：{cap['dataSource']}")
    if cap.get("hook"):
        parts.append(cap["hook"])
    if cap.get("hashtags"):
        parts.append(" ".join(cap["hashtags"]))
    tour = cap.get("tour") or []
    if tour:
        icons = ["📌", "📐", "⚠️", "📊", "🧩", "📈", "🧠", "✅"]
        lines = []
        for i, t in enumerate(tour):
            icon = icons[i] if i < len(icons) else "·"
            lines.append(f"{icon} 图{t['n']}｜{t['text']}")
        parts.append("<br>".join(lines))
    if cap.get("summary"):
        parts.append("✅ " + cap["summary"])
    if cap.get("cta"):
        parts.append(cap["cta"])
    return "<br><br>".join(parts)


# ------------------------------------------------------------------ HTTP
def http_json(url, data=None, headers=None):
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers = dict(headers or {})
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def http_upload(url, file_path):
    boundary = "----wxb" + uuid.uuid4().hex
    ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = head + file_path.read_bytes() + tail
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def get_token(appid, secret):
    q = urllib.parse.urlencode({"grant_type": "client_credential", "appid": appid, "secret": secret})
    res = http_json(f"{API}/token?{q}")
    if "access_token" not in res:
        raise SystemExit(f"获取 access_token 失败: errcode={res.get('errcode')} errmsg={res.get('errmsg')}")
    return res["access_token"]


# ------------------------------------------------------------------ 主流程
def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法: python publish.py deck.json [--push]")
    deck_path = Path(sys.argv[1])
    push = "--push" in sys.argv
    deck = json.loads(deck_path.read_text(encoding="utf-8"))
    meta = deck.get("meta") or {}

    img_dir = OUT / meta["slug"]
    images = sorted(p for p in img_dir.glob("*.png"))
    if not images:
        raise SystemExit(f"没有找到图片：{img_dir}（先跑 build_cards.py）")

    title = meta.get("topic") or meta.get("slug")
    caption = build_caption(deck)
    author = meta.get("author") or "健衡学园"

    print(f"标题: {title}")
    print(f"作者: {author}")
    print(f"图片: {len(images)} 张（{img_dir}）")
    for p in images:
        print(f"  - {p.name}  {p.stat().st_size // 1024} KB")
    print(f"图注: {len(caption)} 字")
    print("-" * 60)
    print(re.sub(r"<br\s*/?>", "\n", caption))
    print("-" * 60)

    if not push:
        print("\n[dry-run] 未调用微信接口。确认无误后加 --push 真正写入草稿箱。")
        return

    appid, secret = credentials()
    print(f"\n凭据: appid={appid[:6]}…  secret=***{len(secret)}")
    token = get_token(appid, secret)
    print("access_token: 已获取")

    media_ids = []
    for p in images:
        url = f"{API}/material/add_material?access_token={token}&type=image"
        res = http_upload(url, p)
        if "media_id" not in res:
            raise SystemExit(f"上传失败 {p.name}: errcode={res.get('errcode')} errmsg={res.get('errmsg')}")
        media_ids.append(res["media_id"])
        print(f"  已上传 {p.name} -> {res['media_id'][:12]}…")

    article = {
        "article_type": "newspic",
        "title": title,
        "author": author,
        "content": caption,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
        "image_info": {"image_list": [{"image_media_id": m} for m in media_ids]},
    }
    payload = {"articles": [article]}
    # 微信要求中文不转义，直接 UTF-8 提交
    req = urllib.request.Request(
        f"{API}/draft/add?access_token={token}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read().decode("utf-8"))

    if res.get("media_id"):
        print(f"\n✅ 已写入草稿箱，media_id={res['media_id']}")
    else:
        raise SystemExit(f"创建草稿失败: errcode={res.get('errcode')} errmsg={res.get('errmsg')}")


if __name__ == "__main__":
    main()
