# -*- coding: utf-8 -*-
"""
健衡学园 · 自定义封面/配图生成
给定提示词文件 → 调用生图后端 → 输出图片。
用于非流水线风格的定制图（如按用户给定的 final prompt 出封面）。

用法:
    python generate-cover.py --prompt-file drafts/xxx/prompt.md --out drafts/xxx/imgs/cover.png [--aspect 2.35:1] [--backend auto|jimeng|qwen-wanxiang]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = ROOT / ".baoyu-skills" / ".env"
COVER_SCRIPTS_DIR = ROOT / ".claude" / "skills" / "baoyu-cover-image" / "scripts"

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_env() -> dict:
    env = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> None:
    parser = argparse.ArgumentParser(description="自定义封面生成")
    parser.add_argument("--prompt-file", required=True, help="提示词文件（全文作提示词）")
    parser.add_argument("--out", required=True, help="输出图片路径（目录自动创建）")
    parser.add_argument("--aspect", default="2.35:1", help="画幅，默认 2.35:1")
    parser.add_argument("--backend", default="auto", choices=["auto", "seedream", "jimeng", "qwen-wanxiang"])
    args = parser.parse_args()

    pf = Path(args.prompt_file)
    if not pf.exists():
        print(json.dumps({"ok": False, "error": f"提示词文件不存在: {pf}"}, ensure_ascii=False))
        sys.exit(1)
    prompt = pf.read_text(encoding="utf-8").strip()
    env = load_env()

    jimeng_ak = (env.get("JIMENG_ACCESS_KEY_ID") or env.get("JIMENG_AK") or "").strip()
    jimeng_sk = (env.get("JIMENG_SECRET_ACCESS_KEY") or env.get("JIMENG_SK") or "").strip()
    qwen_key = env.get("QWEN_API_KEY", "").strip()

    backend = args.backend
    if backend == "auto":
        # 有火山密钥时优先 seedream(4.0) → jimeng(3.0)；否则万相
        if jimeng_ak and jimeng_sk:
            backend = "seedream"
        elif qwen_key:
            backend = "qwen-wanxiang"

    sys.path.insert(0, str(COVER_SCRIPTS_DIR))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if backend in ("seedream", "jimeng"):
        if backend == "seedream":
            from backends.backend_seedream import SeedreamBackend, resolve_seedream_keys
            jimeng_ak, jimeng_sk = resolve_seedream_keys(env)
            inst = SeedreamBackend(jimeng_ak, jimeng_sk)
        else:
            from backends.backend_jimeng import JimengBackend
            inst = JimengBackend(jimeng_ak, jimeng_sk)
        w, h = inst.calculate_dimensions(args.aspect)
        res = inst.generate(prompt, str(out), width=w, height=h)
    elif backend == "qwen-wanxiang":
        from backends.backend_qwen_wanxiang import QwenWanxiangBackend
        size_map = {"2.35:1": "1536x640", "3:2": "1024x768", "16:9": "1280x720", "1:1": "1024x1024"}
        w, h = (int(x) for x in size_map.get(args.aspect, size_map["3:2"]).split("x"))
        res = QwenWanxiangBackend(qwen_key).generate(prompt, str(out), width=w, height=h)
    else:
        print(json.dumps({"ok": False, "error": "未配置任何生图密钥（.baoyu-skills/.env）"}, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res.get("success") else 1)


if __name__ == "__main__":
    main()