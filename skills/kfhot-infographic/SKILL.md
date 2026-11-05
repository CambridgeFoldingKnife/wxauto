---
name: kfhot-infographic
description: 把康复选题或现成文案做成「公众号信息图卡片」（1086×1448 · 3:4 · 青绿医疗科普风）。支持两种输入：① 手动上传文案；② 从 kfhot 康复资讯平台拉今日热点选题。触发词：信息图、卡片图、图文卡片、公众号图片、小绿书、康复信息图、kfhot 选题、做一期卡片、把这篇文章做成图。
---

# kfhot 信息图卡片生成

把一篇文案（或一个热点选题）拆成 8~10 张版面统一的信息图卡片。文字与版式由 HTML 渲染（**零错字**），插画走素材库。

## 一、目录约定

实现全部在仓库 `cards/` 下，skill 只是编排：

```
cards/
├─ build_cards.py              deck.json → HTML → PNG（含溢出/留空自检）
├─ scripts\fetch_topics.py     方式B：拉 kfhot 选题
├─ scripts\validate_deck.py    校验 deck.json（必须过）
├─ scripts\gen_assets.py       万象 2.7 生成插画（一次性）
├─ scripts\alpha_key.py        插画白底转透明
├─ scripts\publish.py          推公众号草稿箱（默认 dry-run）
├─ templates\frame.html        外框
├─ templates\modules.html      9 个模块
├─ assets\                     AI 插画素材（有则用真图，无则用内置 SVG 占位）
├─ deck-cobb.json              示例：Cobb角
├─ deck-stroke.json            示例：脑卒中
└─ out\<slug>\                 产物
```

所有命令都在 `cards\` 目录下执行。

## 二、两种输入

### 方式 A · 手动上传文案

用户给一段文案 / 一个 md 文件 / 一篇已有文章：

1. 读文案，提炼主线（不改变原意、不新增未出现的医学结论）。
2. 按下面的 schema 写 `deck-<slug>.json`。
3. `python scripts/validate_deck.py deck-<slug>.json`
4. `python build_cards.py deck-<slug>.json`

### 方式 B · 自动选题

```bash
python scripts\fetch_topics.py --count 5 --days 7
# 指定主题： --topic 筋膜刀
# 给 agent 读的原始 JSON： --json
```

1. 把候选清单给用户，**让用户挑**（不要自作主张）。
2. 选定后用该候选的 `items`（标题/摘要/链接）+ 领域知识，按 schema 写 deck。
3. 同上跑校验 + 渲染。

> kfhot 地址：默认 `https://kfhot.jianhengyiliao.com`（旧 IP `60.205.181.202:8000` 已下线）。

## 三、deck.json 契约

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
      "blocks": [ { "module": "split-figure", "data": { ... } } ]
    }
  ],
  "caption": { "dataSource": "", "hook": "", "hashtags": [], "tour": [], "summary": "", "cta": "" }
}
```

`title` 里可用 `<em>…</em>` 把关键词渲成青绿色，`<br>` 手动断行。

## 四、九个模块

| 模块 | 用途 | 是否吸收剩余高度 |
| --- | --- | --- |
| `compare-grid` | 分级/分类四列对照 | **是（主块）** |
| `split-figure` | 左文右图 | **是（主块）** |
| `quad-cards` | 四宫格（图标+标题+说明） | 否 |
| `numbered-cols` | 01/02/03 编号三栏 | 否 |
| `statement-band` | 一句话大字面板 | 否（固定 200px） |
| `warning-bar` | 红色提醒条 | 否 |
| `checklist` | ✓ 勾选清单（两列） | 否 |
| `summary-grid` | 编号总结块（两列网格） | 否 |
| `entry-row` | 三张入口卡（图标+标题+说明+箭头） | 否 |

## 五、硬规则（违反就出问题）

1. **每张卡至少要有一个主块**（`compare-grid` 或 `split-figure`）。否则只剩小模块，剩余高度没人吸收，必留大片空白。
2. **一张卡 1 个主块 + 最多 2 个辅块**；超过 3 块容易溢出。
3. `page` 必须从 `01` 连续编号；`titleSize` 取 50~84（字多就调小）。
4. `figure` 只能用这些名字（`assets/` 里的素材名）：
   `body-normal` `body-mild` `body-moderate` `body-severe` `pelvis` `xray-spine` `figure-back`
5. 医学内容**只写有依据的**；数据要能溯源到 `caption.dataSource`。
6. 卡数 8~10 张：01 总览 → 中间知识点 → 最后 1~2 张总结/收藏。

## 六、自检口径

`build_cards.py` 每张都会打印：

```
ok  page=03  slack=0px        # 正常
!! 溢出 page=05 body +37px    # 内容超高，会被切 → 删字或调小 titleSize
!! 留白 page=08 剩余 320px    # 撑不满 → 补内容或换主块
```

**两张都必须清零才算完成。** 别只看图说"差不多"。

## 七、插画素材（万象 2.7）

```bash
python scripts\gen_assets.py --dry              # 只写提示词，0 成本
python scripts\gen_assets.py --only body-normal # 先出 1 张验风格（约 0.5 元）
python scripts\gen_assets.py                    # 生成全部缺失素材（已有会 skip）
python scripts\gen_assets.py --force            # 覆盖
python scripts\alpha_key.py                     # 把白底抠成透明
```

- 风格锁写在 `scripts/gen_assets.py` 顶部的 `STYLE` 常量里，**每次原样拼进提示词，一个字都别改**。
- 第一张成功后自动用 `--ref` 指向它，锁住肤色/光影/构图。
- 生成后自动缩到 720 高（原图 2k 太大），再跑 `alpha_key.py` 抠白底（AI 的白底通常是 `#f8f8f8`，不抠会在面板上留灰块）。
- 素材名固定：`body-normal` `body-mild` `body-moderate` `body-severe` `figure-back` `xray-spine`
  （`pelvis` 目前用内置 SVG——AI 画不出"只画骨盆"的特写，且槽位是横图，不适配）。
- **规范**：一次一张、画面内不能有文字、白底居中、`--ar 9:16 --quality 2k`。

## 八、出图 + 推送

```bash
python build_cards.py deck-xxx.json               # → out/<slug>/*.png
python scripts\publish.py deck-xxx.json           # 默认 dry-run，打印标题/图片/图注
python scripts\publish.py deck-xxx.json --push    # 真正写入公众号草稿箱
```

`publish.py` 直连微信 API（不用 baoyu-post-to-wechat 的 CLI，因为它的 newspic 要求图片出现在正文里，
否则描述会重复显示这一整套图）：

1. `cgi-bin/material/add_material?type=image` 逐张上传 → `media_id`
2. `cgi-bin/draft/add` 提交 `article_type=newspic` + `image_info.image_list`

凭据读 `<项目>/.baoyu-skills/.env` 的 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`。
**推送前必须先 dry-run 看一遍图注。**

## 九、完整流水线

```
方式A 文案 ──┐
             ├─→ deck.json ─→ validate ─→ build ─→ publish --push
方式B kfhot ─┘        ↑                     ↑
                  (agent 写)            assets/（一次性）
```
