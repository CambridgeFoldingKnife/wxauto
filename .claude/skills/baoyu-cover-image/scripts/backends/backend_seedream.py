# -*- coding: utf-8 -*-
"""
Seedream 4.0（即梦4.0 / doubao-seedream）后端
───────────────────────────────────────────
火山引擎 视觉智能 同一套接口：
  Action = CVSync2AsyncSubmitTask / CVSync2AsyncGetResult
  Version = 2022-08-31  |  req_key = jimeng_t2i_v40
请求/查询/取图逻辑完全复用 backend_jimeng（v5 SDK 适配）：
  成功码 10000、查询 action CVSync2AsyncGetResult、查询体带 req_key、
  图片在 data.binary_data_base64[0]（base64 JPEG）。

密钥优先级：SEEDREAM_ACCESS_KEY_ID/SECRET → 回退 JIMENG_*（同一火山账号共用）
环境变量 SEEDREAM_REQ_KEY 可覆盖默认 req_key。
"""
import os

try:
    from backends.backend_jimeng import JimengBackend  # 包内调用路径（scripts/ 在 sys.path）
except ImportError:  # pragma: no cover
    from backend_jimeng import JimengBackend  # 直接运行文件时（backends/ 在 sys.path）


class SeedreamBackend(JimengBackend):
    NAME = "seedream"
    DISPLAY_NAME = "Seedream 4.0 (即梦4.0 文生图)"

    REQ_KEY = os.environ.get("SEEDREAM_REQ_KEY", "jimeng_t2i_v40")


def resolve_seedream_keys(env: dict) -> tuple[str, str]:
    """Seedream 密钥：优先 SEEDREAM_*，留空则复用 JIMENG_*。"""
    ak = (env.get("SEEDREAM_ACCESS_KEY_ID")
          or env.get("JIMENG_ACCESS_KEY_ID")
          or env.get("JIMENG_AK") or "").strip()
    sk = (env.get("SEEDREAM_SECRET_ACCESS_KEY")
          or env.get("JIMENG_SECRET_ACCESS_KEY")
          or env.get("JIMENG_SK") or "").strip()
    return ak, sk


if __name__ == "__main__":
    import sys

    print("usage: 由 illustrate-images.py / generate-cover.py 调用")
    print("SeedreamBackend.REQ_KEY =", SeedreamBackend.REQ_KEY)
    sys.exit(0)