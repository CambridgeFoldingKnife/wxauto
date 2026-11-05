# -*- coding: utf-8 -*-
"""
健衡学园 · 生图并插入流水线
------------------------------------------------------------------
读取定稿 markdown 中的占位标记，生成图片并插回原文：

    <!-- IMG 画面主体描述（只写内容，不写风格） -->
    <!-- COVER 画面主体描述 -->

流程: 解析标记 → 注入"风格锁"拼完整提示词 → 调用生图后端
      （即梦 volcengine / 通义万相 dashscope）→ 下载到 imgs/ → 替换标记为图片引用。

用法:
    python illustrate-images.py --md drafts/2026-09-11-xxx/article.md            # 正式生图
    python illustrate-images.py --md drafts/.../article.md --dry-run             # 只出提示词，不调 API
    python illustrate-images.py --md drafts/.../article.md --backend qwen-wanxiang
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Windows 控制台 UTF-8 适配（避免 GBK 编码报错）
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


def volcengine_legacy_ok() -> bool:
    """
    探测即梦后端真正需要的**旧式** volcengine API 是否可用。

    ★ 不能用 importlib.util.find_spec("volcengine")：
    `volcengine-python-sdk`(5.x) 的子包共享 `volcengine` 前缀，
    会让 find_spec 返回非 None（假阳性），看起来"已装"，
    但运行时 import 依旧失败。
    必须真实 import backend_jimeng.py 用到的那几个符号才算数。

    正确的依赖包是 `volcengine==1.0.228`，不是 `volcengine-python-sdk`。
    """
    try:
        from volcengine.base.Service import Service  # noqa: F401
        from volcengine.ApiInfo import ApiInfo  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False

ROOT = Path(__file__).resolve().parents[4]                    # wxAuto/
CONFIG_PATH = ROOT / "wx-auto-publish.config.json"
ENV_PATH = ROOT / ".baoyu-skills" / ".env"
COVER_SCRIPTS_DIR = ROOT / ".claude" / "skills" / "baoyu-cover-image" / "scripts"

# 风格锁：与 references/image-style-lock.md 保持一致（中文能力强的国内模型可直接用）
STYLE_LOCK = (
    "扁平矢量插画风格，医疗健康科普质感，干净柔和，简洁现代；"
    "主色调为青绿色（#32afaf），辅以奶白、浅蓝、浅灰等低饱和色系，少量金色点缀；"
    "人物为简化扁平风格，不追求真实五官细节；构图留白充足，横构图主体居中或略偏左；"
    "画面无文字、无边框、无水印。"
)

# COVER 标记正则：整行或行内均可
MARKER_RE = re.compile(r"<!--\s*(?P<kind>IMG|COVER)\s*(?P<scene>.*?)\s*-->", re.S)

# 通义万相尺寸档位：仅方形/宽/竖三档，超宽超竖自动归并（封面 2.35:1 → 1280x720，微信可裁）
QWEN_SIZE_MAP = {"2.35:1": "1280x720", "3:2": "1280x720", "16:9": "1280x720", "4:3": "1024x1024", "1:1": "1024x1024"}


def load_json_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {}


def load_env() -> dict:
    """读取 .baoyu-skills/.env（K=V 格式，忽略 # 注释与引号）"""
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


def slugify(scene: str, idx: int) -> str:
    """从画面描述生成安全的文件名片段；含中文，保留前面若干字符。"""
    s = re.sub(r"[^\w一-鿿-]", "", scene.strip())
    s = s[:18]
    return f"{idx:02d}" + (f"-{s}" if s else "")


def pick_backend(pref: str, env: dict) -> tuple[str, dict]:
    """
    后端选择（都有密钥时优先级）：seedream(4.0 画质最好) → jimeng(3.0 旧) → qwen-wanxiang。
    auto 返回第一个候选 + 完整候选链（meta["chain"]），供 main 级失败回退。
    """
    jimeng_ak = (env.get("JIMENG_ACCESS_KEY_ID") or env.get("JIMENG_AK") or "").strip()
    jimeng_sk = (env.get("JIMENG_SECRET_ACCESS_KEY") or env.get("JIMENG_SK") or "").strip()
    seed_ak = (env.get("SEEDREAM_ACCESS_KEY_ID") or jimeng_ak or "").strip()
    seed_sk = (env.get("SEEDREAM_SECRET_ACCESS_KEY") or jimeng_sk or "").strip()
    jimeng_ok = bool(jimeng_ak) and bool(jimeng_sk)
    seed_ok = bool(seed_ak) and bool(seed_sk)
    qwen_ok = bool(env.get("QWEN_API_KEY"))

    if pref in ("seedream", "jimeng", "qwen-wanxiang"):
        return pref, {"chain": [pref]}

    chain = []
    volc_ok = volcengine_legacy_ok()
    if seed_ok and volc_ok:
        chain.append("seedream")
    if jimeng_ok and volc_ok:
        chain.append("jimeng")
    if qwen_ok:
        chain.append("qwen-wanxiang")

    if not chain:
        return "none", {"needs": "JIMENG/SEEDREAM AK+SK（需装 volcengine==1.0.228）或 QWEN_API_KEY", "chain": []}
    # auto 首选仍画质最好的 seedream；失败由 main 沿 chain 回退
    return chain[0], {"chain": chain}


def build_prompts(md_text: str) -> tuple[list[dict], str]:
    """
    遍历 COVER/IMG 标记，生成 {kind, scene, prompt, out_name, width, height} 列表，
    并返回替换标记后的 markdown（正式运行时再落盘）。
    """
    cfg = load_json_config()
    img_cfg = cfg.get("image", {})
    inline_aspect = str(img_cfg.get("aspect_inline", "3:2"))
    cover_aspect = str(img_cfg.get("aspect_cover", "2.35:1"))

    prompts = []
    def repl(m: re.Match) -> str:
        kind, scene = m.group("kind"), m.group("scene").strip()
        if not scene:
            return m.group(0)  # 空标记保留，交回上游处理
        aspect = cover_aspect if kind == "COVER" else inline_aspect
        is_cover = kind == "COVER"
        out_name = "imgs/cover.png" if is_cover else f"imgs/{slugify(scene, len(prompts)+1)}.png"
        prompts.append({
            "kind": kind,
            "scene": scene,
            "prompt": f"{scene}\n\n【风格】{STYLE_LOCK}",
            "out_name": out_name,
            "aspect": aspect,
            "is_cover": is_cover,
        })
        return f"![{kind}图]({out_name})\n"
    replaced = MARKER_RE.sub(repl, md_text)
    return prompts, replaced


def generate_one(backend: str, prompt_doc: dict, env: dict, work_dir: Path) -> dict:
    """调用后端生成单张图片。返回 {ok, path?, error?}"""
    aspect = prompt_doc["aspect"]
    out = work_dir / prompt_doc["out_name"]
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        if backend in ("jimeng", "seedream"):
            sys.path.insert(0, str(COVER_SCRIPTS_DIR))
            if backend == "seedream":
                from backends.backend_seedream import SeedreamBackend, resolve_seedream_keys
                env_ak, env_sk = resolve_seedream_keys(env)
                inst = SeedreamBackend(env_ak, env_sk)
            else:
                from backends.backend_jimeng import JimengBackend  # 旧版 3.0 文生图
                env_ak = (env.get("JIMENG_ACCESS_KEY_ID") or env.get("JIMENG_AK") or "").strip()
                env_sk = (env.get("JIMENG_SECRET_ACCESS_KEY") or env.get("JIMENG_SK") or "").strip()
                inst = JimengBackend(env_ak, env_sk)
            width, height = inst.calculate_dimensions(aspect)
            res = inst.generate(
                prompt_doc["prompt"], str(out), width=width, height=height)
        elif backend == "qwen-wanxiang":
            sys.path.insert(0, str(COVER_SCRIPTS_DIR))
            from backends.backend_qwen_wanxiang import QwenWanxiangBackend
            size = QWEN_SIZE_MAP.get(aspect, QWEN_SIZE_MAP["3:2"])
            w, h = (int(x) for x in size.split("x"))
            model = env.get("QWEN_MODEL") or None
            res = QwenWanxiangBackend(env["QWEN_API_KEY"], model=model).generate(
                prompt_doc["prompt"], str(out), width=w, height=h)
        else:
            return {"ok": False, "error": "未检测到可用生图密钥，请在 .baoyu-skills/.env 填写"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    if res.get("success"):
        return {"ok": True, "path": str(out)}
    return {"ok": False, "error": res.get("error", "未知错误")}


def main() -> None:
    parser = argparse.ArgumentParser(description="健衡学园生图插入")
    parser.add_argument("--md", required=True, help="定稿 markdown 路径")
    parser.add_argument("--dry-run", action="store_true", help="只生成提示词清单，不调用 API")
    parser.add_argument("--backend", choices=["seedream", "jimeng", "qwen-wanxiang", "auto"], default="auto")
    args = parser.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        print(json.dumps({"ok": False, "error": f"文章不存在: {md_path}"}, ensure_ascii=False))
        sys.exit(1)

    work_dir = md_path.parent
    env = load_env()
    backend, meta = pick_backend(args.backend, env)
    backend_chain = meta.get("chain") or ([backend] if backend != "none" else [])

    md_text = md_path.read_text(encoding="utf-8")
    prompts, replaced_md = build_prompts(md_text)

    if not prompts:
        print(json.dumps({"ok": False, "error": "文中没有找到 <!-- IMG ... --> 或 <!-- COVER ... --> 标记"}, ensure_ascii=False))
        sys.exit(1)

    # dry-run：写提示词文件 + 打印清单
    if args.dry_run:
        prompt_dir = work_dir / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(prompts, 1):
            pf = prompt_dir / f"{i:02d}-{p['kind'].lower()}.md"
            pf.write_text(f"# 提示词 {i} [{p['kind']}]\n\n{p['prompt']}\n", encoding="utf-8")
        print(json.dumps({
            "ok": True, "dry_run": True, "backend": backend, "count": len(prompts),
            "items": [{"kind": p["kind"], "scene": p["scene"], "aspect": p["aspect"],
                       "prompt_file": str(prompt_dir / f"{i:02d}-{p['kind'].lower()}.md")}
                      for i, p in enumerate(prompts, 1)],
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    if backend == "none":
        print(json.dumps({"ok": False, "error": "未检测到可用生图后端。请在 .baoyu-skills/.env 填 JIMENG_AK/SK 或 QWEN_API_KEY。"
                                                  "★ 即梦后端依赖必须是 legacy 包 volcengine（版本锁定 1.0.228），不是 volcengine-python-sdk："
                                                  "pip install --index-url https://pypi.org/simple --only-binary :all: \"volcengine==1.0.228\"。"
                                                  "不想装依赖可直接用 --backend qwen-wanxiang（纯 HTTP）。"}, ensure_ascii=False))
        sys.exit(1)

    # 正式生图：沿候选链回退（seedream 权限未开通 / 某后端挂掉时自动换下一个候选）
    results = [None] * len(prompts)
    used_backend = backend
    for attempt in backend_chain:
        pending = [i for i, r in enumerate(results) if r is None or not r.get("ok")]
        if not pending:
            break
        if attempt != used_backend:
            print(f"  [回退] 后端 {used_backend} 有 {len(pending)} 张失败，改用 {attempt} 重试...")
        for i in pending:
            r = generate_one(attempt, prompts[i], env, work_dir)
            results[i] = {**{k: v for k, v in prompts[i].items() if k in ("kind", "scene", "out_name", "aspect")}, **r}
        used_backend = attempt

    # 落盘替换后的 markdown（把成功项对应的图片引用留下，失败项还原为标记便于重试）
    ok_count = 0
    for p, r in zip(prompts, results):
        if isinstance(r, dict) and r.get("ok"):
            ok_count += 1
        else:
            marker = f"<!-- {'COVER' if p['is_cover'] else 'IMG'} {p['scene']} -->"
            placeholder = f"![{'COVER' if p['is_cover'] else 'IMG'}图]({p['out_name']})"
            replaced_md = replaced_md.replace(placeholder, marker)
    md_path.write_text(replaced_md, encoding="utf-8")

    print(json.dumps({"ok": True, "backend": used_backend, "success": ok_count, "failed": len(results) - ok_count,
                      "cover": str(work_dir / "imgs" / "cover.png") if (work_dir / "imgs" / "cover.png").exists() else None,
                      "items": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()