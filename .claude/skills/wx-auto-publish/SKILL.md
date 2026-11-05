---
name: wx-auto-publish
description: 健衡学园公众号自动化发布流水线。输入主题或素材（Word/PDF/TXT），自动完成：素材库选文 → 文案撰写（复刻健衡排版文风）→ 内文配图（生图+插入）→ 封面生成 → 推送到微信草稿箱。用户说"发布公众号文章""wx-auto""用健衡的风格写一篇""公众号流水线" 时触发。
---

# 健衡学园 · 公众号自动化发布流水线

一条命令式流水线，把"选文→写作→配图→排版→推送草稿箱"全部自动化，最后只需人工审核+点击发布。

## 必须先读

- 排版与文风标准：`references/style-guide.md`（**强制**，写作前必读）
- 生图风格锁：`references/image-style-lock.md`（**强制**，配图前必读）

## 首次使用（新环境必读·Agent 自动触发）

> 本 skill 包可整体复制到同事/其他项目的 `.claude/skills/` 下使用（**必须保持
> 项目根/.claude/skills/ 四层结构**，脚本靠相对路径定位项目根，乱放会全断）。
> 仓库里只有 4 个 skill、不含任何项目级配置，第一次使用按下面流程走：

**Agent 触发本 skill 时，先检测项目根是否已初始化：**

```bash
ls 项目根/wx-auto-publish.config.json 项目根/.baoyu-skills/.env 2>/dev/null
```

- 若上述文件**存在** → 已初始化，正常进入 Step 0 体检后开跑。
- 若**缺失**（新环境首次）→ **自动运行首次初始化**：

```bash
python {baseDir}/scripts/setup-new-env.py --check     # 先看缺什么
python {baseDir}/scripts/setup-new-env.py             # 生成缺失配置文件/模板（幂等）
```

初始化脚本会自动：生成 `wx-auto-publish.config.json`、`.baoyu-skills/.env`（密钥模板）、
`EXTEND.md`、`accounts/` 示例账号、`tasks/`/`drafts/`/`素材库/` 目录，并检测 bun、
node_modules、pip 依赖。**然后 agent 必须把下面清单抛给用户逐项确认补齐**（不能跳过）：

1. 打开 `.baoyu-skills/.env` 填入公众号 `WECHAT_APP_ID/WECHAT_APP_SECRET`（引导用户去 mp.weixin.qq.com 获取）；
2. 提醒用户：每个 AppID 都要在公众平台把**本机公网 IP 加入白名单**（否则推送报 ip 不在白名单）；
3. 生图密钥 `JIMENG_*` 或 `QWEN_API_KEY` 二选一填上；
4. 素材库 `素材库/` 可后续投喂 Word/PDF（可选，不投也能用选题池写）。

**Python 依赖安装（★ 版本必须锁定，agent 不得自行放宽版本）**：
```bash
pip install --index-url https://pypi.org/simple --only-binary :all: -r requirements.txt
```
`requirements.txt` 位于项目根目录，已锁死各包可用版本——**尤其即梦 SDK 必须是 `volcengine==1.0.228`，
不可升级到 `volcengine-python-sdk` 5.x**（该版本移除了本仓库依赖的 `volcengine.*` 顶层 API）。
详见「常见问题」表末的说明。

补齐后跑一遍 `check-config.py`，全绿才算就绪。此过程不可由 agent 编造密钥代替用户操作。

## 目录约定

`{baseDir}` = 本 SKILL.md 所在目录。**项目根目录** = `{baseDir}/../../..`（即 ``）。

| 路径 | 用途 |
| --- | --- |
| `wx-auto-publish.config.json` | 流水线配置（素材库路径、画幅、默认作者） |
| `.baoyu-skills/.env` | 密钥（WECHAT_APP_ID/SECRET、JIMENG_AK/SK、QWEN_API_KEY） |
| `drafts/YYYY-MM-DD-<slug>/` | 每次发布的工作目录 |
| `.claude/skills/baoyu-post-to-wechat/` | 排版+推送引擎（含 jianheng 主题） |
| `.claude/skills/baoyu-cover-image/` | 生图后端引擎 |

## 脚本

| 脚本 | 用途 |
| --- | --- |
| `scripts/ingest-knowledge.py` | 扫描素材库，按主题检索并解析文档（docx/pdf/txt/md） |
| `scripts/illustrate-images.py` | 读取定稿 md 中的 `<!-- IMG -->`/`<!-- COVER -->` 标记 → 生图 → 下载 → 插回 md |
| `scripts/generate-cover.py` | 按给定提示词文件生成自定义封面/配图 |
| `scripts/daily-batch.py` | 每日批量计划器：读 accounts/*.json → 算今日任务单（哪些号发/取什么主题）→ 回写节奏状态 |
| `scripts/check-config.py` | 体检：检查配置、密钥、素材库、后端依赖是否就绪 |

## 全链条组合用法（四工具一条龙，不依赖额外记忆）

```
① 选题/取一手素材   → 触发 kfinfo skill（或直接跑 .claude/skills/kfinfo/scripts/kfinfo.py pick / items / hot）
② 写文案            → 本 skill Step 2（按 style-guide）
③ 内文配图         → 本 skill Step 3（illustrate-images.py）
④ 封面             → 本 skill Step 4（generate-cover.py；备选 baoyu-cover-image skill）
⑤ 推送草稿箱       → 本 skill Step 5（wechat-api.ts --theme jianheng；实际引擎=baoyu-post-to-wechat）
```
· kfinfo 提供平台资讯选题（地址可在环境变量 KFHOT_BASE_URL 覆盖）；平台需单独在线。
· baoyu-cover-image skill 可作为手工封面通道；本流水线默认走内置生图脚本。

## 流水线（5 步）

```
输入：主题 / 素材文档
  └→ [1] 素材选文   ingest-knowledge.py --topic "<主题>"
  └→ [2] 文案撰写   Claude 定稿 markdown（style-guide 规范 + IMG/COVER 标记）
  └→ [3] 配图生图   illustrate-images.py --dry-run（预览）→ 确认 → 正式生图
  └→ [4] 排版+封面  渲染验证 + cover.png
  └→ [5] 推送草稿   wechat-api.ts --theme jianheng --cover …
  └→ 完成报告，用户后台审核后自行发布
```

### Step 0：体检（首次/新增配置后必须）

```bash
python {baseDir}/scripts/check-config.py
```
按输出补齐缺失项（通常缺 `.env` 里的密钥，见 `.baoyu-skills/.env` 注释）。

### Step 1：从素材库选文

```bash
python {baseDir}/scripts/ingest-knowledge.py --topic "<主题关键词>" [--limit 5]
```
脚本输出候选文档清单（标题、路径、字数、命中度、摘要）。Claude 根据主题与文案需求选出 1~3 篇，再用 `--extract <文件路径>` 取全文阅读后引用。**未提供素材库路径时**，直接使用用户给的主题/文档，跳过本步。

### Step 2：写文案（最重要的风格复刻）

Claude 按 `references/style-guide.md`：
1. 读所选素材全文，提取要点与数据；
2. 按样板结构（科普型或课程型）撰写 markdown；
3. **frontmatter 必须含** `title`、`description`（摘要）、`author`（默认 健衡学园）；
4. 在需要配图的位置插入独立一行的标记：
   - `<!-- IMG 画面主体描述（只写内容，不写风格） -->`
   - 封面：`<!-- COVER 画面主体描述 -->`（整篇最上方可放 1 个）
   - 内文插图 3~5 个，分布均匀（开头引导、每章 1 张、总结前 1 张）；
5. 文件名：`drafts/YYYY-MM-DD-<slug>/article.md`，存进当天工作目录。

**写作纪律**：每完成一篇，自查一次 style-guide（标题层级、金句加粗、尾注、段落长度）。

### Step 3：配图生图（先预览，再花钱）

```bash
# 3a. 预览：只生成提示词清单，不调 API
python {baseDir}/scripts/illustrate-images.py --md <article.md> --dry-run

# 3b. 用户确认提示词/数量后，正式生图（自动下载并插回 md）
python {baseDir}/scripts/illustrate-images.py --md <article.md> [--backend jimeng|qwen-wanxiang|auto]
```

- 后端选择：`auto` 时优先即梦（若已配 JIMENG 密钥且装了依赖），否则通义万相（无需额外依赖）；
- 图片落盘 `<工作目录>/imgs/`，封面为 `cover.png`，正文图为 `01-<slug>.png` 起；
- 生成完，Claude 向用户展示图片清单并**征求确认**，用户可直接在草稿里换图。

### Step 4：排版验证（可选但推荐）

推送引擎（baoyu-post-to-wechat）会自己渲染，无需预转 HTML；但建议先在本地验证：

```bash
bun ".claude/skills/baoyu-post-to-wechat/scripts/md-to-wechat.ts" <article.md> --theme jianheng
```
检查输出的 temp-article.html：如果愿意，用浏览器/screenshot 看一眼效果再推。

### Step 5：推送草稿箱

> 前置：新环境首次使用前，先在 `.claude/skills/baoyu-post-to-wechat/scripts/` 目录执行 `bun install`（生成 node_modules，含 jianheng 主题等渲染依赖，仓库内不含）。

```bash
bun ".claude/skills/baoyu-post-to-wechat/scripts/wechat-api.ts" <article.md> \
  --theme jianheng \
  --title "<标题>" --author "<作者>" \
  --cover <工作目录>/imgs/cover.png
```
- 若 EXTEND.md 已设默认 theme/author，CLI 可省略；
- **不传 `--summary` 时取 frontmatter description 自动生成**；
- 走 API 直传草稿箱（`draft/add`），返回 media_id。

### Step 6：完成报告

```
已推送到草稿箱（media_id: …）
标题 / 摘要 / 配图 N 张 / 封面
请在 公众号后台 → 内容管理 → 草稿箱 审核后发布：
https://mp.weixin.qq.com
```

---

## 批量模式（多公众号 + 每日定时）

Agent-无关设计：配置文件 + Python 脚本是核心，Claude 只是执行壳（迁移手册见 `AGENT-MIGRATION.md`）。

### 多账号

每个公众号 = `accounts/<alias>.json`（发布配置 + 大纲 + 选题池 + 节奏）。
新增账号步骤见 `accounts/README.md`。公众号密钥放 `.baoyu-skills/.env`：
`WECHAT_<ALIAS>_APP_ID/SECRET`，推送时加 `--account <alias>`。

### 每日批任务流程（调度触发后执行）

```bash
# 1) 计划器算今日任务单（哪些号该发 + 各取什么主题）
python {baseDir}/scripts/daily-batch.py --plan

# 2) 按 tasks/today.json 逐个/并行执行（每号一个子代理，串行也可）：
#    a. 读该号 outline + style-guide，写文章（含 IMG/COVER 标记）
#    b. illustrate-images.py --md <article.md>
#    c. bun .../wechat-api.ts <article.md> --theme <该号theme> --account <alias> --cover ...
# 3) 执行完回写状态：
python {baseDir}/scripts/daily-batch.py --mark
# 4) 汇总审核清单（标题 / media_id / 草稿箱位置）
```

### 会话内定时（Claude 方案）

`CronCreate` 每天触发一次，prompt 为上述批任务流程。注意：
- 仅当 Claude Code 会话打开（空闲）时触发；
- 重复任务 7 天后自动过期，需重新创建（或改用系统计划任务做无人值守，见 AGENT-MIGRATION.md）。

## 配置补全（一次性的）

| 项目 | 位置 | 内容 |
| --- | --- | --- |
| 素材库路径 | `wx-auto-publish.config.json` → `material_dir` | 改成你的本地素材目录 |
| 微信密钥 | `.baoyu-skills/.env` → `WECHAT_APP_ID/SECRET` | 公众平台获取 + IP 白名单 |
| 生图密钥 | 同文件 `JIMENG_AK/SK` 或 `QWEN_API_KEY` | 火山/阿里云获取 |
| 默认账号 | 同文件 `default_author` 或 `.baoyu-skills/baoyu-post-to-wechat/EXTEND.md` | 健衡学园 |

## 常见问题

| 问题 | 处理 |
| --- | --- |
| 缺少 WECHAT_APP_ID | 未填 `.env`；且先跑一次 `check-config.py` |
| 生图失败：`No module named 'volcengine'` | ★ **装错包/装错版本了**。本仓库 `backend_jimeng.py` 用的是**旧式 API**（`volcengine.ApiInfo` / `volcengine.Credentials` / `volcengine.ServiceInfo` / `volcengine.base.Service`），而 `volcengine-python-sdk` **5.x 已移除顶层 `volcengine` 命名空间**（只剩 `volcenginesdk*` 子包），装它必失败。<br>**正确装法（版本必须锁死）**：`pip install --index-url https://pypi.org/simple --only-binary :all: "volcengine==1.0.228"`<br>或直接 `pip install -r requirements.txt`（仓库根目录已锁好全部版本）。<br>务必装 `volcengine` 而**非** `volcengine-python-sdk`；`--only-binary :all:` 可避免 `pycryptodome` 现场编译。也可改用 qwen-wanxiang 后端绕开该依赖。 |
| 装完仍报找不到 `volcengine`，或检测说"已装"却跑不起来 | 很可能是装成了 5.x 新版（子包同前缀会让 `find_spec` 假阳性）。用真实 import 验证：`python -c "from volcengine.base.Service import Service; print('OK')"`；不 OK 就卸掉重装 1.0.228 |
| pip 装包报 `No matching distribution found` | 默认镜像源不通。显式加 `--index-url https://pypi.org/simple` |
| 生图全部报「未知错误」 | 多为 seedream4.0 未开通（火山 50400 Access Denied）；改用 `--backend jimeng`（3.0）兜底，或开通 jimeng_t2i_v40 权限 |
| qwen-wanxiang 报 404 | 该后端接口需核对 DashScope 模型名/大小档位；本地主用即梦即可 |
| 推送/渲染报 `Missing theme CSS for "xxx"` 或"主题不存在" | ★ **主题名写错了**。公司品牌主题名**只能是 `jianheng`**（对应 `themes/jianheng.css`）。<br>❌ 常见错写：`jianhengxueyuan` / `jianheng-xueyuan` / `jianheng_xueyuan`（后者是**账号 alias**，不是主题名）。<br>✅ 本副本 `.baoyu-skills/baoyu-post-to-wechat/EXTEND.md` 已预设 `default_theme: jianheng`，**保持默认、不要改**。<br>另需确认已执行第 1.5 步把 `theme-overrides/jianheng.css` 拷进 `node_modules/baoyu-md/dist/themes/`（`bun install` 不会装它）。 |
| 想发布到健衡康复资讯 | 暂改 EXTEND.md 的 `default_author`，或启用多账号块 |