# -*- coding: utf-8 -*-
"""即梦 (jimeng) 后端单图冒烟测试：v5 SDK 适配后 提交→轮询→下载 全流程。"""
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

ak = env.get("JIMENG_ACCESS_KEY_ID", "").strip()
sk = env.get("JIMENG_SECRET_ACCESS_KEY", "").strip()
print("AK 前缀:", (ak[:8] + "...") if ak else "(空)", "| SK 长度:", len(sk))

b = JimengBackend(ak, sk)
w, h = b.calculate_dimensions("2.35:1")
prompt = ("久坐上班族肩颈酸痛、物理治疗师为其做体态评估的扁平插画。"
          "扁平矢量插画风格，医疗健康科普质感，主色调青绿色，低饱和色系，"
          "简化扁平人物，留白充足，横构图，无文字无水印。")
out = ROOT / "drafts" / "2026-09-11-jianjingtong" / "imgs"
out.mkdir(parents=True, exist_ok=True)

res = b.generate(prompt, str(out / "cover.png"), width=w, height=h)
print("生成结果:", json.dumps(res, ensure_ascii=False))
if res.get("success"):
    size = (out / "cover.png").stat().st_size
    print(f"cover.png 大小: {size} 字节")
sys.exit(0 if res.get("success") else 1)