---
name: kfinfo
description: 康复资讯聚合平台(kfhot)查询客户端。调用 kfhot 对外接口获取康复/物理治疗领域最新资讯、按主题或关键词检索、获取自动选题素材包、体检平台健康,为公众号写作提供一手信源。触发词:"获取康复资讯""kfhot""kfinfo""最新康复""康复选题""康复素材""康复热点"。
---

# kfinfo · 康复资讯查询(kfhot 客户端)

查询「康复资讯聚合平台」(kfhot)——一台公网常驻、每天自动抓取(国际英文首发 + 国内学会动态 + 营销/培训选题)的**康复领域信源库**。调用它对接到的是**真实数据和真实链接**,可直接作为公众号写作的第一手素材。

## 平台信息

- 数据源地址(公网):`http://60.205.181.202:8000`(可被环境变量 `KFHOT_BASE_URL` 覆盖)
- **前置**:kfhot 平台需独立在线(它是一台常驻服务);若换环境/换机/换端口,用 `KFHOT_BASE_URL` 指到新地址再调。平台部署与运维说明见项目根目录 `ECS运维手册.md`。
- 数据形态:每条 = 标题 + 来源 + 原文链接(DOI/URL) + 主题标签(肩颈腰腿痛/脑卒中康复/心脏康复/青少年体态/运动损伤/物理治疗是什么) + 分级(`权威`=期刊/学会/医院,`次权威`=营销号/转载/培训) + 摘要
- 只存摘要+链接,不存全文(版权红线);写作时引用思路而非搬全文

## 调用方式(推荐:走脚本,输出 JSON)

```bash
python .claude/skills/kfinfo/scripts/kfinfo.py <子命令> [参数]
```

| 子命令 | 用途 | 示例 |
|---|---|---|
| `hot` | 近 N 日热点榜 | `kfinfo.py hot --days 7 --limit 10` / `--tier 权威` / `--topic 脑卒中康复` |
| `items` | 多条件检索(写作引素材主力) | `kfinfo.py items --keyword stroke --lang en` / `--topic 心脏康复` / `--tier 次权威` |
| `item` | 单条详情 | `kfinfo.py item --id 1` |
| `featured` | 每日精选(三档各一篇) | `kfinfo.py featured` |
| `daily` | 行业日报聚合 | `kfinfo.py daily` |
| `pick` | **自动选题包**(N 个“主题+方向+素材”) | `kfinfo.py pick --count 5` / `--tier 次权威` |
| `secondary` | 次权威快捷口(营销/转载选题) | `kfinfo.py secondary` |
| `topics` | 六主题中英关键词 | `kfinfo.py topics` |
| `health` | 平台体检(总量/来源新鲜度/断源) | `kfinfo.py health` |

也可直接 `curl`/浏览器打 `http://60.205.181.202:8000/api/v1/...`(全开放、无鉴权)。

## 按需求挑接口(工作流)

1. **今天康复圈有什么新货** → `hot`
2. **写某主题文章要素材** → `items --topic <主题>` 或 `items --keyword <词>`
3. **英文文献首发/最新研究** → `items --lang en`(加 `--tier 权威` 只看期刊/学会)
4. **要一批“今天写什么”的选题** → `pick --count N`(核心,给写作流程喂选题)
5. **营销/广告类选题(公众号流量向)** → `secondary` 或 `pick --tier 次权威`
6. **发稿前确认平台没挂/源是否新鲜** → `health`

## 注意事项

- **参数值**:主题用中文(六主题名之一);`keyword` 中英文都支持;`tier` 只取 `权威` 或 `次权威`,留空=全部混排;
- **不要编造接口**:只有上面 10 个;`/docs` 是交互文档页,不是数据接口;
- **数据新鲜度**:平台每天 8/14/20 点自动抓取 + 联网搜索,是"滚动的新鲜库",但非实时搜索——需要给结论时注明"取材自 kfhot 平台,截止最近一次抓取";
- **避免重复请求**:一次 `pick/items` 拿够素材即可,别对同一查询反复打;
- **可用性**:平台偶发维护时返回连接错误,按脚本提示重试或检查 `health`。

## 示例输出(强调用什么)

`python kfinfo.py hot --days 7` 返回形如:

```json
{ "count": 10, "items": [
  { "id": 6, "title": "Effect of Hamstring Stretching on ...",
    "source": "Europe PMC·康复领域(期刊+预印本首发)", "url": "https://doi.org/10.1002/pri.70310",
    "topic_tags": ["肩颈腰腿痛"], "tier": "权威", "lang": "en", "published_at": "2026-10-01" } ] }
```

## 与写作流水线的衔接

- 本文档给 **Agent 取料**;公众号写作、排版、推送仍走 `wx-auto-publish` 流水线(健衡排版文风);
- 写稿时优先 `pick` 选题 → `items` 补料 → **换一种表达**写成公众号模板文章,并保留 `source/url` 溯源。