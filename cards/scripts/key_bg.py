# -*- coding: utf-8 -*-
"""从四角泛洪填充，把"与边缘同色"的背景变成透明。

比阈值法稳：白底、黑底、带轻微渐变的底都能处理，且不会误伤画面内部的白色区域。

用法:
  python key_bg.py            # 处理 assets 下全部 png
  python key_bg.py --tol 24
  python key_bg.py --file x.png
"""
import sys
from collections import deque
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def key(path, tol=20):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()

    # 取"边框众数色"作为背景基准：黑底、白底、浅灰底都能覆盖
    from collections import Counter
    border = []
    for x in range(w):
        border.append(px[x, 0]); border.append(px[x, h - 1])
    for y in range(h):
        border.append(px[0, y]); border.append(px[w - 1, y])
    base = Counter(border).most_common(1)[0][0]
    seen = bytearray(w * h)
    dq = deque()
    for sx, sy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        i = sy * w + sx
        if not seen[i]:
            seen[i] = 1
            dq.append((sx, sy))

    while dq:
        x, y = dq.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                i = ny * w + nx
                if seen[i]:
                    continue
                c = px[nx, ny]
                if abs(c[0] - base[0]) <= tol and abs(c[1] - base[1]) <= tol and abs(c[2] - base[2]) <= tol:
                    seen[i] = 1
                    dq.append((nx, ny))

    alpha = Image.new("L", (w, h), 255)
    ap = alpha.load()
    for y in range(h):
        row = y * w
        for x in range(w):
            if seen[row + x]:
                ap[x, y] = 0

    out = im.convert("RGBA")
    out.putalpha(alpha)
    out.save(path, optimize=True)

    total = w * h
    bg = sum(seen)
    print(f"  {path.name}: {w}x{h}  背景 {bg / total:.0%} 已透明  底色={base}")


def main():
    args = sys.argv[1:]
    tol = 20
    if "--tol" in args:
        tol = int(args[args.index("--tol") + 1])
    if "--file" in args:
        files = [ASSETS / args[args.index("--file") + 1]]
    else:
        files = sorted(ASSETS.glob("*.png"))
    for f in files:
        if f.exists():
            key(f, tol)
        else:
            print(f"  skip {f.name}")


if __name__ == "__main__":
    main()
