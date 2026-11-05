# 康复信息图卡片工作流

把一篇康复科普文案（或 kfhot 上的热点选题）做成一套**版式统一的信息图卡片**，并可直接推进公众号草稿箱。

```
选题 / 文案 ──→ deck.json ──→ 校验 ──→ 10 张 PNG ──→ 图注 ──→ 公众号草稿箱
                  ↑                        ↑
              (人写/模型写)            assets/ 插画素材
```

## 为什么用 HTML 而不是直接生图

| 做法 | 结果 |
| --- | --- |
| **HTML 渲染**（本方案） | 文字零错字、可参数化、改一个字重渲染 1 秒 |
| 整张交给生图模型 | 中文必错（实测 `Cobb`→`Cobh`）、10 张风格不统一、不可复现 |

分工很明确：**版式和文字归 HTML，写实插画归 AI**。两者各干各的强项。

---

## 目录结构

```
cards/
├─ build_cards.py          deck.json → HTML → PNG（含溢出/留空自检）
├─ _base.css               基础样式（所有主题都基于它）
├─ render.sh               简易渲染脚本（渲染当前目录所有 *.html）
├─ deck-cobb.json          示例：脊柱侧弯 Cobb角（10 张）
├─ deck-stroke.json        示例：脑卒中康复（9 张）
├─ templates/
│  ├─ frame.html           外框：顶栏 / 标题 / 金句条 / 页脚 / 水印
│  └─ modules.html         9 个内容模块
├─ themes/
│  ├─ academic.css         主题 A · 学术文献风
│  └─ data.css             主题 E · 极简数据风
├─ scripts/
│  ├─ fetch_topics.py      从 kfhot 拉选题候选
│  ├─ validate_deck.py     校验 deck.json（页码/模块/主块/素材名）
│  ├─ gen_assets.py        万象 2.7 生成插画（一次性）
│  ├─ alpha_key.py         阈值法抠白底（旧方案，保留备查）
│  ├─ key_bg.py            泛洪填充抠底（推荐，黑白底都适用）
│  └─ publish.py           推公众号草稿箱（默认 dry-run）
├─ previews/
│  └─ make_previews.py     同一张卡的 4 种内容策略预览
├─ prompts/
│  ├─ ref-cobb01-fullcard.md   复刻整张卡的生图提示词（实测用）
│  └─ assets/*.md              每个素材的最终提示词（可复现）
├─ assets/                 已定稿的插画素材（透明背景）
└─ out/                    产物（已 gitignore）
```

---

## 快速开始

**依赖**：Python 3.9+、Chrome 或 Edge（用于渲染）。生成插画另需 `bun` + 万象 API Key。

```bash
cd cards

# 1. 校验
python scripts/validate_deck.py deck-cobb.json

# 2. 出图（默认主题）
python build_cards.py deck-cobb.json

# 3. 换主题
python build_cards.py deck-cobb.json --theme academic
```

产物在 `out/<slug>/`，例如 `out/cobb-angle/01-compare-grid+entry-row.png`（1086×1448，3:4）。

---

## 两种输入

### A · 手动文案

把文章读一遍 → 按 `deck.json` 契约写成卡片结构 → 校验 → 出图。
参考 `deck-stroke.json`（由一篇真实文章转换而来）。

### B · 自动选题

```bash
python scripts/fetch_topics.py --count 5 --days 7
python scripts/fetch_topics.py --topic 筋膜刀
python scripts/fetch_topics.py --json          # 给 agent 读
```

输出选题候选（主题 / 方向 / 来源 / 素材条数）。选定后把素材交给模型展开成 `deck.json`。

> kfhot 地址默认 `https://kfhot.jianhengyiliao.com`（旧 IP `60.205.181.202:8000` 已下线），可用 `KFHOT_BASE_URL` 覆盖。

---

## deck.json 契约

```json
{
  "meta": {
    "slug": "stroke-golden-period",
    "topic": "脑卒中康复黄金期",
    "series": "脑卒中康复 ｜ 黄金期与居家训练",
    "category": "家属必看",
    "sideRight": "早开始<br>早规范<br>恢复空间更大",
    "sideKey": "以专业<br>守护每一份坚持",
    "keyFoot": "科学判断 · 尽早开始 · 长期坚持",
    "watermark": "健衡学园 · 康复科普"
  },
  "cards": [
    {
      "page": "01",
      "titleSize": 62,
      "title": "脑卒中康复<br><em>怎么判断还在黄金期？</em>",
      "titlePlain": "脑卒中康复怎么判断还在黄金期",
      "subbar": "家属最常问的一个问题",
      "key": "康复介入越早越好，但从来都不算晚",
      "keySize": 32,
      "blocks": [{ "module": "split-figure", "data": { } }]
    }
  ],
  "caption": {
    "dataSource": "…", "hook": "…", "hashtags": [],
    "tour": [], "summary": "…", "cta": "…"
  }
}
```

- `title` 里可用 `<em>…</em>` 渲成青绿色、`<br>` 手动断行
- `page` 必须从 `01` 连续编号
- `titleSize` 取 50~84（字多就调小）

---

## 九个模块

| 模块 | 用途 | 吸收剩余高度 |
| --- | --- | --- |
| `compare-grid` | 分级/分类四列对照 | ✅ 主块 |
| `split-figure` | 左文右图 | ✅ 主块 |
| `quad-cards` | 四宫格（图标+标题+说明） | — |
| `numbered-cols` | 01/02/03 编号三栏 | — |
| `statement-band` | 一句话大字面板 | — |
| `warning-bar` | 红色提醒条 | — |
| `checklist` | 勾选清单（两列） | — |
| `summary-grid` | 编号总结块 | — |
| `entry-row` | 三张入口卡（带箭头） | — |

### 硬规则

1. **每张卡至少要有一个主块**（`compare-grid` / `split-figure`），否则剩余高度没人吸收，必留大片空白。
2. 一张卡 **1 个主块 + 最多 2 个辅块**，超过 3 块容易溢出。
3. 素材名只能用 `assets/` 里实际存在的名字。

---

## 自检口径

`build_cards.py` 每张卡都会打印：

```
ok  page=03  slack=0px                                  # 正常
!! 溢出   page=05 body +37px                            # 内容超高，会被切
!! 面板内溢出 page=02 panel +12px                        # 面板内部裁掉了标题
!! 留白   page=08 剩余 320px                             # 撑不满，会出大片空白
```

**三项都必须清零才算完成**，不要靠肉眼判断。

---

## 主题

```bash
python build_cards.py deck-cobb.json --theme academic   # 学术文献风：宋体、左对齐、细线
python build_cards.py deck-cobb.json --theme data       # 极简数据风：无卡片、大数字、单色
```

主题只是 `themes/*.css` 覆盖 `_base.css`，**`deck.json` 不需要改**。新增主题＝新增一个 css 文件。

---

## 插画素材

```bash
python scripts/gen_assets.py --dry               # 只写提示词，0 成本
python scripts/gen_assets.py --only body-normal  # 先生成 1 张验风格
python scripts/gen_assets.py                     # 补齐缺失素材
python scripts/key_bg.py                         # 白底/黑底 → 透明（推荐）
```

- 风格锁写在 `gen_assets.py` 的 `STYLE` 常量里，**每次原样拼进提示词，不要改**
- 第一张成功后自动 `--ref` 指向它，锁住肤色/光影/构图
- 生成后自动缩到 720 高；再用 `key_bg.py` 抠底（AI 的白底通常是 `#f8f8f8`，不抠会在面板上留灰块）
- 素材名固定：`body-normal` `body-mild` `body-moderate` `body-severe` `figure-back` `xray-spine`

> **素材是按题材定稿的。** 换题材需要补新插画（约 0.5 元/张）；同题材复用为 0 元。

---

## 推送公众号草稿箱

```bash
python scripts/publish.py deck-cobb.json          # dry-run：打印标题/图片/图注
python scripts/publish.py deck-cobb.json --push   # 真正写入草稿箱
```

流程：`g2/ci-bin/material/add_material` 逐张上传拿 `media_id` → `draft/add` 提交 `article_type=newspic`。

**注意**
- 凭据读 `.baoyu-skills/.env` 的 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`
- 公众号后台需把**当前公网 IP** 加入白名单，家用宽带 IP 会变（`errcode=40164` 就是这个原因）
- `newspic` 的 `author` 字段会被微信丢弃，属正常现象

---

## 配置

在项目根 `.baoyu-skills/.env` 中（**不要提交到仓库**，仓库里只放 `.env.example`）：

```
WECHAT_APP_ID=
WECHAT_APP_SECRET=
DASHSCOPE_API_KEY=          # 万象 2.7 生图
KFHOT_BASE_URL=https://kfhot.jianhengyiliao.com
```

---

## 已知限制

1. **万象没有 3:4 档位**（只有 1:1 / 16:9 / 9:16）。所以 AI 只出"白底居中人体"，画幅由 HTML 槽位决定。
2. **插画与题材绑定**：`body-*` / `xray-spine` 只服务脊柱侧弯，换题材要补图。
3. **每张卡必须有主块**，否则版面会空——这是模板结构决定的，不是 bug。
4. 卡片数量目前靠人写 `deck.json` 控制；"按 N 页自动分块"的编排层尚未实现。
