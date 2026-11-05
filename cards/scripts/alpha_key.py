# -*- coding: utf-8 -*-
"""把素材的"接近白"的背景抠成透明（AI 出的白底通常是 #f8f8f8，不是纯白）。

用法:
  python alpha_key.py                 # 处理 body-* / figure-back
  python alpha_key.py --all           # 处理 assets 下全部 png
  python alpha_key.py --file x.png    # 处理指定文件

阈值：三通道最小值 >= 245 → 全透明；<= 238 → 保留；中间做线性过渡，避免锯齿。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
TARGETS = ["body-normal", "body-mild", "body-moderate", "body-severe", "figure-back", "xray-spine"]


def key_one(path):
    im = Image.open(path).convert("RGB")
    r, g, b = im.split()
    m = ImageChops.darker(ImageChops.darker(r, g), b)      # 三通道最小值
    alpha = m.point(lambda v: 0 if v >= 240 else (255 if v <= 232 else int((240 - v) * 255 / 8)))
    im = im.convert("RGBA")
    im.putalpha(alpha)
    im.save(path, optimize=True)
    # 统计剩余不透明比例
    hist = alpha.histogram()
    opaque = sum(hist[250:])
    total = im.width * im.height
    print(f"  {path.name}: {im.width}x{im.height}  不透明 {opaque / total:.0%}")


def main():
    args = sys.argv[1:]
    if "--file" in args:
        files = [ASSETS / args[args.index("--file") + 1]]
    elif "--all" in args:
        files = sorted(ASSETS.glob("*.png"))
    else:
        files = [ASSETS / (n + ".png") for n in TARGETS]

    for f in files:
        if f.exists():
            key_one(f)
        else:
            print(f"  skip {f.name}（不存在）")


if __name__ == "__main__":
    main()
