# -*- coding: utf-8 -*-
"""
健衡学园 · 环境体检
检查流水线所需：配置、密钥、运行时、主题、素材库、后端依赖是否就绪。
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

# Windows 控制台 UTF-8 适配（避免 GBK 编码报错）
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = ROOT / "wx-auto-publish.config.json"
ENV_PATH = ROOT / ".baoyu-skills" / ".env"
THEME_CSS = ROOT / ".claude" / "skills" / "baoyu-post-to-wechat" / "scripts" / "node_modules" / "baoyu-md" / "dist" / "themes" / "jianheng.css"
API_SCRIPT = ROOT / ".claude" / "skills" / "baoyu-post-to-wechat" / "scripts" / "wechat-api.ts"
EXTEND = ROOT / ".baoyu-skills" / "baoyu-post-to-wechat" / "EXTEND.md"


def read_env() -> dict:
    env = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def report(ok: bool, label: str, detail: str = "") -> None:
    print(("✅" if ok else "❌"), label, detail)


def main() -> None:
    print(f"项目根目录: {ROOT}\n")

    # 1. 流水线配置
    cfg = {"material_dir": ""}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            report(False, "wx-auto-publish.config.json", "无法解析(JSON 错误)")
    else:
        report(False, "wx-auto-publish.config.json", "缺失")

    material = str(cfg.get("material_dir") or "")
    if material and "路径" not in material:
        report(True, "素材库配置", material)
    elif material and "路径" in material:
        report(False, "素材库配置", "仍是占位文本，请改成真实路径")
    else:
        report(False, "素材库配置", "未配置（流水线将改用直接给主题/文档的方式）")

    # 2. 密钥
    env = read_env()
    report(bool(env.get("WECHAT_APP_ID")), "WECHAT_APP_ID", "(微信公众号 AppID)")
    report(bool(env.get("WECHAT_APP_SECRET")), "WECHAT_APP_SECRET", "(微信公众号 AppSecret)")
    jimeng_ak = env.get("JIMENG_ACCESS_KEY_ID") or env.get("JIMENG_AK") or ""
    jimeng_sk = env.get("JIMENG_SECRET_ACCESS_KEY") or env.get("JIMENG_SK") or ""
    jimeng = bool(jimeng_ak.strip()) and bool(jimeng_sk.strip())
    seed_ak = (env.get("SEEDREAM_ACCESS_KEY_ID") or jimeng_ak).strip()
    seed_sk = (env.get("SEEDREAM_SECRET_ACCESS_KEY") or jimeng_sk).strip()
    seedream = bool(seed_ak) and bool(seed_sk)
    qwen = bool(env.get("QWEN_API_KEY"))
    report(jimeng, "JIMENG AK/SK", "(即梦 3.0·火山引擎)")
    report(seedream, "Seedream 4.0", "(即梦4.0，复用 JIMENG 密钥即可，req_key=jimeng_t2i_v40)")
    report(qwen, "QWEN_API_KEY", "(通义万相·DashScope)")
    if not (jimeng or qwen):
        print("  → 提示：.env 位置 " + str(ENV_PATH) + "\n")

    # 3. 运行时
    bun = shutil.which("bun")
    report(bool(bun), f"bun: {bun}" if bun else "bun 运行时", "(排版/推送引擎需要，已装则展示路径)")
    py = sys.version_info
    report(py >= (3, 9), f"Python {py.major}.{py.minor}", "(脚本要求 ≥3.9)")

    # 4. 主题与引擎
    report(THEME_CSS.exists(), "jianheng 主题", "baoyu-md/dist/themes/jianheng.css")
    report(API_SCRIPT.exists(), "推送引擎", "baoyu-post-to-wechat/scripts/wechat-api.ts")
    ext = EXTEND.exists()
    report(ext, "EXTEND.md", "baoyu-post-to-wechat 发布配置" if ext else "缺失")
    if ext and "jianheng" in EXTEND.read_text(encoding="utf-8"):
        pass  # 主题已设为默认

    # 5. 生图后端依赖
    report(bool(importlib.util.find_spec("volcengine")), "volcengine-python-sdk", "(即梦后端依赖；缺则不能用即梦)")
    report(bool(importlib.util.find_spec("pypdf") or importlib.util.find_spec("PyPDF2")), "pypdf", "(素材库 PDF 解析；缺则 PDF 无法检索)")
    print("\n体检完成。缺失项见上方 ❌。")


if __name__ == "__main__":
    main()