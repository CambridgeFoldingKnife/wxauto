# -*- coding: utf-8 -*-
"""一次性生成信息图插画素材（万象 2.7）

用法:
  python gen_assets.py --dry                 # 只写提示词文件，不生图（0 成本）
  python gen_assets.py --only body-normal    # 只生一张
  python gen_assets.py                       # 生成全部缺失素材
  python gen_assets.py --force               # 覆盖已有素材

约定（直接决定风格一致性，别改）：
  - 一次只生成一张
  - 画面内不允许出现任何文字/数字/符号
  - 纯白背景、全身居中、四周留边
  - 第一张成功后，后续自动用 --ref 指向它锁风格
"""
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]        # cards/
ASSETS = ROOT / "assets"
PROMPTS = ROOT / "prompts" / "assets"
SKILL = Path(os.path.expanduser("~")) / ".qoder-cn" / "skills" / "baoyu-image-gen" / "scripts" / "main.ts"

PROVIDER = "dashscope"
MODEL = "wan2.7-image-pro"
AR = "9:16"
QUALITY = "2k"

# ---------- 风格锁：每次原样拼在最前面，一个字都不要改 ----------
STYLE = """医学康复科普插画，写实精确的医学解剖插画风格（detailed medical illustration, realistic anatomy, 不是照片，不是卡通，不是线稿）。
背面视角的成年人体，只见后脑与头发，看不到面部与五官。
肤色均匀偏暖（#f7cdae），有柔和的体积光影，线条干净。
纯白色背景（#ffffff），无地面阴影、无背景元素、无边框。
人体全身入画、居中放置，四周留出空白边距。
【绝对禁止】画面内出现任何文字、数字、字母、符号、水印、签名、标尺、箭头标注。
沿脊柱绘制一条鲜红色（#e0342f）的粗实线，线条平滑、粗细均匀。
肩、腰、臀、腿比例符合成年人解剖，双臂自然垂放于身体两侧。
"""

ASSET_SPECS = {
    "body-normal": "本次姿态：脊柱笔直，无明显侧弯；双肩水平、骨盆水平，躯干左右对称。",
    "body-mild": "本次姿态：脊柱呈轻微 S 形侧弯（约 15 度），右侧肩胛略高，躯干轻微不对称。",
    "body-moderate": "本次姿态：脊柱明显 S 形侧弯（约 30 度），一侧背部隆起（剃刀背），骨盆略倾斜。",
    "body-severe": "本次姿态：脊柱严重 S 形侧弯（超过 45 度），躯干明显变形，一侧背部大幅隆起，双臂与躯干间距明显不对称。",
    "pelvis": "本次画面：只画骨盆与臀部背面（不含上半身），两条臀部轮廓清晰，中间可见臀沟；脊柱下段向下延伸，画一条红色粗线。",
    "xray-spine": "本次画面：站立位全脊柱 X 光片风格的医学示意图（灰度），可见椎体与椎间隙，脊柱呈轻度 S 形弯曲；在上下端椎处各画一条蓝色短参考线，用一条红色虚线连接这两处。纯白色背景。",
    "figure-back": "本次画面：稍宽松构图的全身背面人体，肩胛与骨盆轮廓清晰，脊柱一条鲜红色曲线；整体更接近信息图插图，留白更多。",
}



def downscale(path, max_h=720):
    """卡片槽位最大约 400px，原图 2048 高太大，统一缩到 720 高，省得产物 PNG 过大。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            if im.height <= max_h:
                return
            ratio = max_h / im.height
            im = im.convert("RGB").resize((max(1, int(im.width * ratio)), max_h), Image.LANCZOS)
            im.save(path, optimize=True)
    except Exception as e:
        print("  (缩图跳过:", e, ")")

def prompt_for(name):
    return STYLE + "\n" + ASSET_SPECS[name] + "\n"


def already(name):
    return (ASSETS / (name + ".png")).exists()


def generate(name, ref=None, force=False):
    out = ASSETS / (name + ".png")
    if already(name) and not force:
        print(f"skip  {name}（已存在，用 --force 覆盖）")
        return out

    PROMPTS.mkdir(parents=True, exist_ok=True)
    pf = PROMPTS / (name + ".md")
    pf.write_text(prompt_for(name), encoding="utf-8")
    print(f"prompt {pf.relative_to(ROOT)}")

    cmd = [
        "bun", str(SKILL),
        "--promptfiles", str(pf),
        "--image", str(out),
        "--provider", PROVIDER,
        "--model", MODEL,
        "--ar", AR,
        "--quality", QUALITY,
    ]
    if ref and Path(ref).exists():
        cmd += ["--ref", str(ref)]

    print(f"gen   {name}  ({MODEL}, {AR}, {QUALITY})" + ("  ref=" + Path(ref).name if ref else ""))
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not out.exists():
        print("  !! 失败")
        tail = ((proc.stderr or "") + (proc.stdout or ""))[-600:]
        print("  " + tail.replace("\n", "\n  "))
        return None
    downscale(out)
    print(f"  ok  {out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")
    return out


def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    force = "--force" in args
    only = None
    if "--only" in args:
        only = args[args.index("--only") + 1]

    ASSETS.mkdir(exist_ok=True)

    if dry:
        for name in (ASSET_SPECS.keys() if only is None else [only]):
            PROMPTS.mkdir(parents=True, exist_ok=True)
            (PROMPTS / (name + ".md")).write_text(prompt_for(name), encoding="utf-8")
            print(f"已写 prompts/assets/{name}.md（0 成本，未生图）")
        return

    names = [only] if only else list(ASSET_SPECS.keys())

    # 第一张成功的图作为后续的 --ref，锁住肤色/光影/构图
    ref = None
    for name in names:
        if ref is None:
            for cand in ("body-normal", "figure-back", "pelvis"):
                p = ASSETS / (cand + ".png")
                if p.exists():
                    ref = p
                    break
        r = generate(name, ref=ref, force=force)
        if r and ref is None and name != "pelvis":
            ref = r

    print("\n完成。把 PNG 放进 cards/assets/ 后重跑 build_cards.py，模板会自动换成真素材。")


if __name__ == "__main__":
    main()
