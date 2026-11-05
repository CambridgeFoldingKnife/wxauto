# -*- coding: utf-8 -*-
"""deck.json -> 1086x1448 卡片 PNG

用法:
  python build_cards.py deck-cobb.json                 # 生成 HTML + 出图 + 溢出检查
  python build_cards.py deck-cobb.json --no-render     # 只生成 HTML
  python build_cards.py deck-cobb.json --no-check      # 跳过溢出检查(快)

产物:
  cards/.build/NN-<module>.html   (供人调试)
  cards/out/<slug>/NN-<module>.png
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"
BUILD = ROOT / ".build"
OUT = ROOT / "out"
ASSETS = ROOT / "assets"

CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# ---------------------------------------------------------------- helpers
def find_chrome():
    for c in CHROMES:
        if Path(c).exists():
            return c
    raise SystemExit("找不到 Chrome / Edge，无法渲染")


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{{%s}}" % k.upper(), str(v))
    return tpl


def load_modules():
    text = (TPL / "modules.html").read_text(encoding="utf-8")
    parts = re.split(r"<!--#([a-z-]+)-->", text)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def asset_or_svg(name, svg, css=""):
    """assets/<name>.png 存在就用真素材，否则用占位 SVG（M1 阶段）"""
    if name and (ASSETS / (name + ".png")).exists():
        return '<img class="figslot" src="../assets/%s.png" alt="" style="%s">' % (name, css)
    return svg

# ---------------------------------------------------------------- 占位插画
SPINE = {
    "normal":   "M75 52 C75 90 75 140 75 180",
    "mild":     "M75 52 C84 90 66 140 75 180",
    "moderate": "M75 52 C92 88 58 146 78 180",
    "severe":   "M75 52 C98 84 50 150 84 180",
}
SHADE = {"normal": 0, "mild": 0.18, "moderate": 0.25, "severe": 0.33}


def body_svg(spine, w=117, h=250):
    skin, outline, red = "#f7cdae", "#dfa985", "#e0342f"
    return f'''<svg class="figslot" width="{w}" height="{h}" viewBox="0 0 150 320" xmlns="http://www.w3.org/2000/svg">
<rect x="53" y="176" width="21" height="134" rx="10" fill="{skin}" stroke="{outline}" stroke-width="2"/>
<rect x="76" y="176" width="21" height="134" rx="10" fill="{skin}" stroke="{outline}" stroke-width="2"/>
<rect x="35" y="64" width="16" height="92" rx="8" fill="{skin}" stroke="{outline}" stroke-width="2"/>
<rect x="99" y="64" width="16" height="92" rx="8" fill="{skin}" stroke="{outline}" stroke-width="2"/>
<path d="M53 60 C53 58 62 50 75 50 C88 50 97 58 97 60 C102 72 102 88 98 102 C95 114 98 126 102 138 C105 152 102 168 95 178 L55 178 C48 168 45 152 48 138 C52 126 55 114 52 102 C48 88 48 72 53 60 Z" fill="{skin}" stroke="{outline}" stroke-width="2"/>
<rect x="67" y="44" width="16" height="12" fill="{skin}"/>
<ellipse cx="75" cy="28" rx="19" ry="23" fill="{skin}" stroke="{outline}" stroke-width="2"/>
<path d="M52 92 C72 88 96 94 100 106 C104 122 98 142 92 152 C80 160 58 158 50 146 C46 130 48 106 52 92 Z" fill="#6f6047" opacity="{SHADE[spine]}"/>
<path d="{SPINE[spine]}" stroke="{red}" stroke-width="5" fill="none" stroke-linecap="round"/>
</svg>'''


def pelvis_svg(spine, w=107, h=80):
    path = {
        "normal":   "M75 10 L75 60",
        "mild":     "M75 10 C80 30 71 46 75 60",
        "moderate": "M75 10 C90 32 62 46 78 60",
        "severe":   "M75 10 C98 34 56 48 84 60",
    }[spine]
    return f'''<svg class="pelvis" width="{w}" height="{h}" viewBox="0 0 150 112" xmlns="http://www.w3.org/2000/svg">
<path d="M18 10 C34 0 116 0 132 10 C140 42 132 80 112 96 C94 108 56 108 38 96 C18 80 10 42 18 10 Z" fill="#f7cdae" stroke="#dfa985" stroke-width="2"/>
<ellipse cx="55" cy="76" rx="26" ry="25" fill="#eebd9b"/>
<ellipse cx="95" cy="76" rx="26" ry="25" fill="#eebd9b"/>
<path d="M75 62 C75 78 75 92 75 102" stroke="#dfa985" stroke-width="3" fill="none"/>
<path d="{path}" stroke="#e0342f" stroke-width="5" fill="none" stroke-linecap="round"/>
</svg>'''


def xray_svg():
    verts = []
    for i in range(11):
        t = i / 10
        y = 40 + t * 400
        x = 180 + 40 * math.sin(t * math.pi * 1.15)
        w = 36 - 8 * abs(0.5 - t)
        rot = 9 * math.sin(t * 3.2)
        verts.append(
            f'<rect x="{x - w / 2:.1f}" y="{y:.1f}" width="{w:.1f}" height="26" rx="6" '
            f'fill="#d3dce2" stroke="#b3c0ca" stroke-width="1.5" '
            f'transform="rotate({rot:.1f} {x:.1f} {y:.1f})"/>'
        )
    top_y, bot_y = 96, 372
    top_x = 180 + 40 * math.sin(0.14 * math.pi * 1.15)
    bot_x = 180 + 40 * math.sin(0.83 * math.pi * 1.15)
    return f'''<svg viewBox="0 0 360 480" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">
<rect x="20" y="10" width="320" height="440" rx="18" fill="#f4f7f9"/>
{''.join(verts)}
<line x1="{top_x - 70:.0f}" y1="{top_y}" x2="{top_x + 70:.0f}" y2="{top_y - 14}" stroke="#2f8fd6" stroke-width="3"/>
<line x1="{bot_x - 70:.0f}" y1="{bot_y}" x2="{bot_x + 70:.0f}" y2="{bot_y + 12}" stroke="#2f8fd6" stroke-width="3"/>
<line x1="{top_x}" y1="{top_y}" x2="{bot_x}" y2="{bot_y}" stroke="#e0342f" stroke-width="4" stroke-dasharray="10 8"/>
<circle cx="{top_x:.0f}" cy="{top_y}" r="7" fill="#2f8fd6"/>
<circle cx="{bot_x:.0f}" cy="{bot_y}" r="7" fill="#2f8fd6"/>
</svg>'''


def figure_back_svg():
    return '''<svg viewBox="0 0 320 420" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">
<ellipse cx="160" cy="52" rx="34" ry="42" fill="#f7cdae" stroke="#dfa985" stroke-width="2"/>
<path d="M96 128 C96 112 120 100 160 100 C200 100 224 112 224 128 C232 168 228 224 216 268 C210 292 218 320 228 344 C236 366 228 392 212 404 L108 404 C92 392 84 366 92 344 C102 320 110 292 104 268 C92 224 88 168 96 128 Z" fill="#f7cdae" stroke="#dfa985" stroke-width="2"/>
<path d="M160 108 C172 160 148 240 168 316" stroke="#e0342f" stroke-width="7" fill="none" stroke-linecap="round"/>
<path d="M120 140 C138 130 182 130 200 140" stroke="#e9b894" stroke-width="3" fill="none"/>
<path d="M112 250 C140 262 180 262 208 250" stroke="#e9b894" stroke-width="3" fill="none"/>
</svg>'''


def vertebra_svg(color="#fff"):
    bars = "".join(
        f'<rect x="{15 if i % 2 == 0 else 12}" y="{i * 9}" width="{16 if i % 2 == 0 else 22}" height="8" rx="4" fill="{color}"/>'
        for i in range(7)
    )
    return f'<svg width="42" height="64" viewBox="0 0 42 64" xmlns="http://www.w3.org/2000/svg">{bars}</svg>'


def split_figure(name, kind="xray"):
    if name and (ASSETS / (name + ".png")).exists():
        return '<img class="figslot" src="../assets/%s.png" alt="">' % name
    if name == "figure-back":
        return figure_back_svg()
    return xray_svg()


def entry_icon(kind):
    if kind == "lung":
        return ('<svg width="36" height="36" viewBox="0 0 34 34">'
                '<path d="M17 4 v10" stroke="#fff" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
                '<path d="M17 12 c-6 2 -9 7 -9 13 a5 5 0 0 0 5 5 h2 a3 3 0 0 0 3 -3 V12 z" fill="#fff"/>'
                '<path d="M17 12 c6 2 9 7 9 13 a5 5 0 0 1 -5 5 h-2 a3 3 0 0 1 -3 -3 V12 z" fill="#fff"/>'
                '</svg>')
    if kind == "clip":
        return ('<svg width="34" height="34" viewBox="0 0 32 32">'
                '<rect x="6" y="6" width="20" height="23" rx="4" fill="#fff"/>'
                '<rect x="11" y="2" width="10" height="7" rx="2.5" fill="#fff"/>'
                '<path d="M11 15 h10 M11 20 h10 M11 25 h6" stroke="#8a7ff0" stroke-width="2.2" stroke-linecap="round"/>'
                '</svg>')
    return kind

# ---------------------------------------------------------------- 模块渲染
def build_block(mod, data, mods):
    tpl = mods[mod]
    if mod == "compare-grid":
        items = ""
        for i, c in enumerate(data["columns"], 1):
            sp = c.get("spine", "normal")
            fig = asset_or_svg(c.get("figure"), body_svg(sp))
            pel = pelvis_svg(sp) if c.get("pelvis") else ""
            items += (
                f'<div class="grade g{i}"><div class="num">{c["num"]}</div>'
                f'<div class="figrow"><div class="angle">{c["angle"]}</div>{fig}</div>'
                f'<div class="tri"></div><div class="name">{c["name"]}</div>'
                f'<div class="range">{c["range"]}</div>{pel}</div>'
            )
        return fill(tpl, head=data["head"], sub=data["sub"], items=items)

    if mod == "split-figure":
        note = ""
        if data.get("note"):
            note = (
                f'<div class="measure" style="margin-top:16px">'
                f'<div class="mt">{data.get("noteTitle", "")}</div>'
                f'<div class="md">{data["note"]}</div></div>'
            )
        return fill(
            tpl,
            head=data["head"],
            body=data["body"],
            note=note,
            figure=split_figure(data.get("figure")),
            figcap=data.get("figCaption", ""),
        )

    if mod == "quad-cards":
        cells = "".join(
            f'<div class="cell c{i}"><div class="badge">{c["badge"]}</div>'
            f'<div class="ct">{c["title"]}</div><div class="cd">{c["desc"]}</div></div>'
            for i, c in enumerate(data["cells"], 1)
        )
        return fill(tpl, items=cells)

    if mod == "numbered-cols":
        cols = "".join(
            f'<div class="numcol"><div class="nbadge">{c["n"]}</div>'
            f'<div class="nt">{c["title"]}</div><div class="nd">{c["desc"]}</div></div>'
            for c in data["cols"]
        )
        return fill(tpl, items=cols)

    if mod == "statement-band":
        extra = ""
        if data.get("note"):
            extra = (
                f'<div class="measure" style="margin-top:18px">'
                f'<div class="mt">{data.get("noteTitle", "")}</div>'
                f'<div class="md">{data["note"]}</div></div>'
            )
        return fill(tpl, text=data["text"], extra=extra)

    if mod == "warning-bar":
        return fill(tpl, text=data["text"])

    if mod == "checklist":
        items = "".join(f"<li>{x}</li>" for x in data["items"])
        return fill(tpl, title=data["title"], items=items)

    if mod == "summary-grid":
        items = "".join(
            f'<div class="sblock"><div class="snum">{x["n"]}</div>'
            f'<div><div class="st">{x["title"]}</div><div class="sd">{x["desc"]}</div></div></div>'
            for x in data["items"]
        )
        return fill(tpl, items=items)

    if mod == "entry-row":
        chev = (
            '<svg class="chev" width="30" height="30" viewBox="0 0 30 30">'
            '<circle cx="15" cy="15" r="14" fill="currentColor" opacity=".14"/>'
            '<path d="M12.5 9 L18.5 15 L12.5 21" stroke="currentColor" stroke-width="2.4" '
            'fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        )
        items = "".join(
            f'<div class="entry e{i}"><div class="ico">{entry_icon(c.get("icon", "?"))}</div>'
            f'<div class="txt"><div class="t">{c["title"]}</div><div class="d">{c["desc"]}</div></div>'
            f'{chev}</div>'
            for i, c in enumerate(data["entries"], 1)
        )
        return fill(tpl, items=items)

    raise SystemExit("未知模块: " + mod)

# ---------------------------------------------------------------- 主流程
def main():
    args = [a for a in sys.argv[1:]]
    deck_path = next((a for a in args if not a.startswith("--")), None)
    if not deck_path:
        raise SystemExit("用法: python build_cards.py deck.json [--no-render] [--no-check]")
    render = "--no-render" not in args
    check = "--no-check" not in args
    theme = None
    if "--theme" in args:
        theme = args[args.index("--theme") + 1]
    theme_css = "../themes/%s.css" % theme if theme else ""

    deck = json.loads(Path(deck_path).read_text(encoding="utf-8"))
    meta = deck["meta"]
    mods = load_modules()
    frame = (TPL / "frame.html").read_text(encoding="utf-8")

    BUILD.mkdir(exist_ok=True)
    out_dir = OUT / (meta["slug"] + ("--" + theme if theme else ""))
    out_dir.mkdir(parents=True, exist_ok=True)

    chrome = find_chrome() if render else None
    made = []
    problems = []

    for card in deck["cards"]:
        body = "\n".join(build_block(b["module"], b["data"], mods) for b in card["blocks"])
        html = fill(
            frame,
            category=meta["category"],
            series=meta["series"],
            page=card["page"],
            side_right=meta["sideRight"],
            title_size=card["titleSize"],
            title_html=card["title"],
            title_plain=card["titlePlain"],
            subbar=card["subbar"],
            body=body,
            key_size=card.get("keySize", 33),
            key_text=card["key"],
            side_key=meta["sideKey"],
            key_foot=meta["keyFoot"],
            watermark=meta["watermark"],
            theme_css=theme_css,
        )
        names = "+".join(b["module"] for b in card["blocks"])
        name = f'{card["page"]}-{names}'
        hp = BUILD / (name + ".html")
        hp.write_text(html, encoding="utf-8")
        made.append(hp)
        print("HTML  ", hp.relative_to(ROOT))

        if not render:
            continue

        url = "file:///" + hp.as_posix().lstrip("/")
        png = out_dir / (name + ".png")

        if check:
            r = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--virtual-time-budget=1500",
                 "--dump-dom", url],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            m = re.search(r"OVF=(-?\d+)\s+CARD=(-?\d+)\s+SLACK=(-?\d+)\s+PANEL=(-?\d+)", r.stdout or "")
            if m:
                ovf, cardof, slack, panelof = (int(m.group(i)) for i in (1, 2, 3, 4))
                if panelof > 0:
                    problems.append((card["page"], "面板内溢出", f"panel +{panelof}px（标题可能被裁）"))
                    print(f"  !! 面板内溢出 page={card['page']} +{panelof}px")
                elif ovf > 0 or cardof > 0:
                    problems.append((card["page"], "溢出", f"body +{ovf}px / card +{cardof}px"))
                    print(f"  !! 溢出 page={card['page']} body+{ovf}px card+{cardof}px")
                elif slack > 60:
                    problems.append((card["page"], "留白", f"剩余 {slack}px"))
                    print(f"  !! 留白 page={card['page']} 剩余 {slack}px")
                else:
                    print(f"  ok  page={card['page']}  slack={slack}px")

        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1", "--window-size=1086,1448",
             "--default-background-color=FFFFFFFF", "--screenshot=" + str(png), url],
            capture_output=True,
        )
        print("PNG   ", png.relative_to(ROOT))

    print()
    print(f"完成：{len(made)} 张，输出目录 {out_dir.relative_to(ROOT)}")
    if problems:
        print(f"⚠️  {len(problems)} 张需要调整：")
        for p in problems:
            print(f"   page {p[0]}  {p[1]}：{p[2]}")


if __name__ == "__main__":
    main()
