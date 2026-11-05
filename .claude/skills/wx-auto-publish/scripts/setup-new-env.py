# -*- coding: utf-8 -*-
"""
健衡学园 · 新环境首次初始化（First-Run Setup）
==================================================================
把只含 4 个 skill 包的仓库初始化为可运行状态。幂等：已存在的文件/目录一律跳过，
绝不覆盖用户数据。运行后按输出的清单补齐密钥即可开跑流水线。

使用场景：
  - 同事第一次拿到 skill 包，agent 检测到项目根缺配置时自动触发
  - 手动：python setup-new-env.py [--check]

做了四件事：
  1. 定位项目根（= 本文件 ../../..，即 wxAuto/）
  2. 生成缺失的项目级配置文件（config.json / .env 模板 / EXTEND.md / accounts 示例 / 目录）
  3. 检测运行时（bun / node_modules / pip 包）
  4. 输出剩余人工步骤清单
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 控制台 UTF-8 适配（避免 GBK 编码报错）
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parents[4]          # wxAuto/（scripts→wx-auto-publish→skills→.claude→根）
SKILLS_DIR = ROOT / ".claude" / "skills"
ENV_DIR = ROOT / ".baoyu-skills"
CONFIG_PATH = ROOT / "wx-auto-publish.config.json"
ENV_PATH = ENV_DIR / ".env"
EXTEND_DIR = ENV_DIR / "baoyu-post-to-wechat"
EXTEND_PATH = EXTEND_DIR / "EXTEND.md"
ACCOUNTS_DIR = ROOT / "accounts"
TASKS_DIR = ROOT / "tasks"
DRAFTS_DIR = ROOT / "drafts"
MATERIAL_DIR = ROOT / "素材库"
WECHAT_ENGINE_DIR = SKILLS_DIR / "baoyu-post-to-wechat" / "scripts"

CONFIG_TEMPLATE = {
    "material_dir": "素材库",
    "drafts_dir": "drafts",
    "account": "jianheng-xueyuan",
    "theme": "jianheng",
    "default_author": "健衡学园",
    "image": {
        "style": "扁平插画风（医疗科普感）",
        "preferred_backend": "auto",
        "num_min": 3,
        "num_max": 5,
        "aspect_inline": "3:2",
        "aspect_cover": "2.35:1",
    },
}

ENV_TEMPLATE = """# 健衡学园 · 密钥文件（.claude/skills 首次初始化自动生成，请人工填写）
# ── 微信公众号 ──────────────────────────────────────────────
# 在 https://mp.weixin.qq.com → 设置与开发 → 基本配置 获取
# 注意：每个 AppID 都要在公众平台把"本机公网 IP"加入白名单
#       （"已 IP 白名单的服务器"），否则推送会提示 ip 不在白名单。
WECHAT_APP_ID=
WECHAT_APP_SECRET=

# 多号时追加（可选）：alias 大写化的前缀
# WECHAT_JIANHENG_XUEYUAN_APP_ID=
# WECHAT_JIANHENG_XUEYUAN_APP_SECRET=

# ── 生图：即梦 3.0（火山引擎）───────────────────────────────
# 控制台 https://console.volcengine.com/ark → API Key 管理
# 取 AccessKey/SecretKey（AK/SK 二选一命名风格都识别）
JIMENG_ACCESS_KEY_ID=
JIMENG_SECRET_ACCESS_KEY=
# 或
# JIMENG_AK=
# JIMENG_SK=

# ── 生图备选：通义万相（DashScope，无需额外 SDK）────────────
# https://bailian.console.aliyun.com → API-KEY
QWEN_API_KEY=

# ── kfhot 康复资讯平台（可选，默认公网地址，可换成自己的部署）──
# KFHOT_BASE_URL=http://60.205.181.202:8000
"""

EXTEND_TEMPLATE = """# 健衡学园 · 公众号发布配置
#
# ★ default_theme 必须保持 `jianheng`（公司品牌主题，随包提供）。
#   ⚠️ 不要写成 jianhengxueyuan / jianheng-xueyuan —— 主题文件名是 jianheng.css，
#      写错会报：Error: Missing theme CSS for "xxx": .../themes/xxx.css
#      注意：`jianheng-xueyuan` 是【账号 alias】，不是主题名。
default_theme: jianheng
default_publish_method: api
default_author: 健衡学园
need_open_comment: 1
only_fans_can_comment: 0

# ── 多账号（需要发布到其他号时启用） ──
# accounts:
#   - name: 健衡学园
#     alias: jianheng-xueyuan
#     default: true
"""

ACCOUNT_TEMPLATE = {
    "alias": "jianheng-xueyuan",
    "name": "健衡学园",
    "theme": "jianheng",
    "author": "健衡学园",
    "image_style": "扁平插画风（医疗科普感）",
    "cadence": {"daily": True},
    "outline": {
        "定位": "专注康复教育，推动专业前行",
        "目标读者": "物理治疗师、康复师、运动康复从业者、慢病/术后患者家属",
        "写作样板": "科普型",
        "选题池": [
            {"主题": "肩颈腰腿痛", "方向": "物理治疗视角久坐族自救指南"},
            {"主题": "脑卒中康复", "方向": "黄金期判断与居家训练要点"},
            {"主题": "心脏康复", "方向": "运动处方与生活回归"},
            {"主题": "青少年体态", "方向": "脊柱侧弯/含胸驼背的早期识别"},
            {"主题": "运动损伤", "方向": "崴脚/膝痛的正确处理流程"},
            {"主题": "物理治疗是什么", "方向": "面向大众的学科科普"},
        ],
    },
}


def yes(label: str, detail: str = "") -> None:
    print(("✅" if detail else "◎"), label, detail)


def wait_for(t):  # noqa: ANN001 - 兼容旧 Python 的 typing 简写
    return t


def ensure_write(path: Path, content: str) -> None:
    """文件不存在才写，绝不覆盖已有内容。"""
    if path.exists():
        print("◎ 已存在，跳过:", path.relative_to(ROOT))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("✅ 已生成:", path.relative_to(ROOT))


def ensure_write_json(path: Path, obj: dict) -> None:
    if path.exists():
        print("◎ 已存在，跳过:", path.relative_to(ROOT))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("✅ 已生成:", path.relative_to(ROOT))


def main() -> None:
    check_only = "--check" in sys.argv
    print(f"新环境初始化 · 项目根: {ROOT}\n")

    # ── 0. 路径约定自查 ─────────────────────────────────────
    if not (SKILLS_DIR / "wx-auto-publish" / "SKILL.md").exists():
        print("❌ 路径约定破坏：4 个 skill 必须放在", SKILLS_DIR, "下")
        print("   （脚本用 parents[3] 定位项目根），源码结构请勿改动\n")
        return
    yes("skill 包路径约定", "4 个 skill 位于 .claude/skills/ 下")

    # ── 1. 项目级配置文件 ───────────────────────────────────
    if not check_only:
        ensure_write(CONFIG_PATH, json.dumps(CONFIG_TEMPLATE, ensure_ascii=False, indent=2) + "\n")
        ensure_write(ENV_PATH, ENV_TEMPLATE)
        ensure_write(EXTEND_PATH, EXTEND_TEMPLATE)
        ensure_write(ACCOUNTS_DIR / "jianheng-xueyuan.json",
                     json.dumps(ACCOUNT_TEMPLATE, ensure_ascii=False, indent=2) + "\n")
        for d in (ACCOUNTS_DIR, TASKS_DIR, DRAFTS_DIR, MATERIAL_DIR):
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                print("✅ 已创建目录:", d.relative_to(ROOT))

    # ── 2. 运行时检测 ───────────────────────────────────────
    print("\n—— 运行时检测 ——")
    bun = shutil.which("bun")
    yes("bun 运行时", str(bun) if bun else "(缺失：需安装 node 版 bun，或 npx -y bun 临时替代)")
    nm = WECHAT_ENGINE_DIR / "node_modules"
    yes("推送引擎依赖 node_modules", "已装" if nm.exists() else "(缺失：在 baoyu-post-to-wechat/scripts 下执行 bun install)")
    if bun and not nm.exists() and not check_only:
        print("  → 自动执行 bun install ...")
        try:
            subprocess.run([bun, "install"], cwd=str(WECHAT_ENGINE_DIR),
                           check=False, capture_output=True)
        except Exception as e:  # noqa: BLE001
            print("  → bun install 异常:", e)
        print("   完成（node_modules =", nm.exists(), "）")

    # ── 3. kfhot 平台连通性（可选） ─────────────────────────
    print("\n—— kfhot 康复资讯平台 ——")
    print("  kfinfo 是客户端；平台需在线。地址可用环境变量 KFHOT_BASE_URL 覆盖。")
    print("  首次使用建议先跑: python .claude/skills/kfinfo/scripts/kfinfo.py health")

    # ── 4. 剩余人工步骤清单 ─────────────────────────────────
    print("\n—— 还需人工完成的步骤（自检项） ——")
    steps = [
        f"1. 编辑 {ENV_PATH}：填入 WECHAT_APP_ID/WECHAT_APP_SECRET（公众号后台获取）",
        "2. 在公众平台把本机公网 IP 加入白名单（每个 AppID 独立，换机/换网要重加）",
        f"3. 生图密钥：填 JIMENG_*（火山引擎）或 QWEN_API_KEY（通义万相），二选一即可",
        "4. 【★ 版本必须锁定】装 Python 依赖（勿自行升级版本）：",
        "   pip install --index-url https://pypi.org/simple --only-binary :all: -r requirements.txt",
        "   └ 即梦 SDK 必须是 volcengine==1.0.228，装 volcengine-python-sdk(5.x) 会报找不到模块；",
        "     验证： python -c \"from volcengine.base.Service import Service; print('OK')\"",
        "   └ 不想装依赖就改用 --backend qwen-wanxiang（纯 HTTP，无需 SDK）",
        "5. 【★ 主题名别写错】品牌主题名是 jianheng（不是 jianhengxueyuan）：",
        "   .baoyu-skills/baoyu-post-to-wechat/EXTEND.md 已预设 default_theme: jianheng，保持默认即可，勿改",
        "   └ 写错会报：Error: Missing theme CSS for \"xxx\"（找不到 themes/xxx.css）",
        "   └ jianheng-xueyuan 只是【账号 alias】，跟主题名是两回事",
        "6. 素材库：倒入 Word/PDF 到 素材库/（可选）或直接用选题池+领域知识写稿",
        "7. 校验：python .claude/skills/wx-auto-publish/scripts/check-config.py",
    ]
    for s in steps:
        print("  " + s)

    # ── 5. 汇总 check-config 体检 ───────────────────────────
    print("\n—— 调用 check-config 复检 ——")
    subprocess.run([sys.executable, str(ROOT / ".claude" / "skills" / "wx-auto-publish" / "scripts" / "check-config.py")],
                   check=False)


if __name__ == "__main__":
    main()