# -*- coding: utf-8 -*-
"""校验 deck.json 是否符合卡片模板的约束

用法:
  python validate_deck.py deck-cobb.json

退出码: 0 通过 / 1 有错误
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ALLOWED_MODULES = {
    "compare-grid", "split-figure", "quad-cards", "numbered-cols",
    "statement-band", "warning-bar", "checklist", "summary-grid", "entry-row",
}
# 带图/能吸收高度的"主块"——每张卡至少要有一个，否则必留大片空白
FLEX_MODULES = {"compare-grid", "split-figure"}
FIGURES = {
    "body-normal", "body-mild", "body-moderate", "body-severe",
    "pelvis", "xray-spine", "figure-back",
}
META_KEYS = ["slug", "topic", "series", "category", "sideRight", "sideKey", "keyFoot", "watermark"]
CAPTION_KEYS = ["dataSource", "hook", "hashtags", "tour", "summary", "cta"]


def check(deck_path):
    errs, warns = [], []
    try:
        deck = json.loads(Path(deck_path).read_text(encoding="utf-8"))
    except Exception as e:
        return [f"JSON 解析失败: {e}"], []

    meta = deck.get("meta") or {}
    for k in META_KEYS:
        if not meta.get(k):
            errs.append(f"meta 缺字段: {k}")

    cards = deck.get("cards") or []
    if not cards:
        errs.append("cards 为空")

    seen = set()
    for idx, c in enumerate(cards, 1):
        tag = f"第 {idx} 张 (page={c.get('page')})"
        page = c.get("page")
        if not page:
            errs.append(f"{tag}: 缺 page")
        elif page in seen:
            errs.append(f"{tag}: page 重复")
        seen.add(page)
        if page != f"{idx:02d}":
            errs.append(f"{tag}: page 应为 {idx:02d}，页码必须连续")

        ts = c.get("titleSize", 0)
        if not isinstance(ts, int) or not (50 <= ts <= 84):
            errs.append(f"{tag}: titleSize 须为 50~84 的整数（当前 {ts}）")

        for k in ("title", "titlePlain", "subbar", "key"):
            if not c.get(k):
                errs.append(f"{tag}: 缺 {k}")

        blocks = c.get("blocks") or []
        if not blocks:
            errs.append(f"{tag}: blocks 为空")
            continue
        mods = [b.get("module") for b in blocks]
        for m in mods:
            if m not in ALLOWED_MODULES:
                errs.append(f"{tag}: 未知模块 {m}")
        if not (set(mods) & FLEX_MODULES):
            errs.append(f"{tag}: 缺少带图主块（compare-grid / split-figure），会留大片空白")

        # 素材名检查
        for b in blocks:
            d = b.get("data") or {}
            figs = []
            if d.get("figure"):
                figs.append(d["figure"])
            for col in (d.get("columns") or []):
                if col.get("figure"):
                    figs.append(col["figure"])
            for f in figs:
                if f not in FIGURES:
                    errs.append(f"{tag}: 未知素材名 {f}（可用: {', '.join(sorted(FIGURES))}）")

        if len(blocks) > 3:
            warns.append(f"{tag}: blocks {len(blocks)} 个，偏多，注意溢出")

    cap = deck.get("caption") or {}
    for k in CAPTION_KEYS:
        if not cap.get(k):
            warns.append(f"caption 缺 {k}")

    return errs, warns


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法: python validate_deck.py deck.json")
    errs, warns = check(sys.argv[1])
    for w in warns:
        print("⚠️  " + w)
    for e in errs:
        print("❌ " + e)
    if errs:
        print(f"\n校验失败：{len(errs)} 个错误")
        sys.exit(1)
    print(f"✅ 校验通过（{len(warns)} 条提醒）")


if __name__ == "__main__":
    main()
