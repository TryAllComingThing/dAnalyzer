# 搜索来源站点目录

> 按搜索角度分类的可信来源清单。Phase 3 并行搜索时，将对应 `allowed_domains` 传入 WebSearch。
> 本文件为推荐清单，不强制穷举 — 研究主题特化时可追加领域专属来源。

---

## 通用可信来源（所有搜索角度共享）

| 来源 | 域名 | 说明 |
|------|------|------|
| Wikipedia | en.wikipedia.org | 百科综述（需交叉验证，不可作为唯一来源） |
| 百度百科 | baike.baidu.com | 中文百科（同上限制） |
| Google Scholar | scholar.google.com | 学术文献检索 |
| Semantic Scholar | semanticscholar.org | AI 驱动的学术搜索 |

---

## 1. 核心主题语义

自然语言描述搜索，不限定特定域名。优先信任来源见「通用可信来源」。

---

## 2. 技术/专业关键词

| 来源 | allowed_domains | 适用场景 |
|------|-----------------|----------|
| 官方技术文档 | 取决于具体技术（如 python.org, react.dev, kubernetes.io） | 技术原理、API、架构 |
| GitHub | github.com | 开源项目、代码实现、issue 讨论 |
| Stack Overflow | stackoverflow.com | 技术问答、实践问题 |
| 机器之心 | jiqizhixin.com | AI/ML 中文技术报道 |
| Papers with Code | paperswithcode.com | AI 论文 + 代码实现 |
| IEEE Xplore | ieeexplore.ieee.org | 工程技术论文 |

---

## 3. 2024-2026 最新进展

| 来源 | allowed_domains | 适用场景 |
|------|-----------------|----------|
| TechCrunch | techcrunch.com | 科技/创业公司动态 |
| The Verge | theverge.com | 科技产品/行业 |
| 36氪 | 36kr.com | 中国科技/创投 |
| 虎嗅 | huxiu.com | 中国科技/商业深度 |
| 晚点 LatePost | latepost.com | 中国商业深度报道 |
| Wired | wired.com | 科技趋势/文化 |
| Ars Technica | arstechnica.com | 技术深度分析 |
| MIT Technology Review | technologyreview.com | 技术趋势/商业化 |

---

## 4. 学术/研究视角

| 来源 | allowed_domains | 适用场景 |
|------|-----------------|----------|
| arXiv | arxiv.org | 预印本（CS/AI/统计/物理） |
| Google Scholar | scholar.google.com | 通用学术检索 |
| Semantic Scholar | semanticscholar.org | AI 强化学术搜索 |
| PubMed | pubmed.ncbi.nlm.nih.gov | 生物医学 |
| SSRN | ssrn.com | 社科/经济/金融预印本 |
| ResearchGate | researchgate.net | 学术社交网络 |
| 中国知网 | cnki.net | 中文学术文献 |
| 万方数据 | wanfangdata.com.cn | 中文学术文献 |
| ScienceDirect | sciencedirect.com | Elsevier 期刊全文 |
| Springer Link | link.springer.com | Springer 期刊/会议 |

---

## 5. 批判性视角 / 反面观点

| 来源 | allowed_domains | 适用场景 |
|------|-----------------|----------|
| Reddit | reddit.com | 社区讨论（按 subreddit 筛选） |
| Hacker News | news.ycombinator.com | 技术社区讨论 |
| Trustpilot | trustpilot.com | 产品/服务用户评价 |
| G2 | g2.com | B2B 软件用户评价 |
| 知乎 | zhihu.com | 中文深度问答/行业讨论 |
| V2EX | v2ex.com | 中文技术社区 |

---

## 6. 行业/市场趋势

| 来源 | allowed_domains | 适用场景 |
|------|-----------------|----------|
| Gartner | gartner.com | IT 市场研究/Magic Quadrant |
| Statista | statista.com | 统计数据/市场数据 |
| CB Insights | cbinsights.com | 风投/科技市场分析 |
| McKinsey | mckinsey.com | 管理咨询/行业报告 |
| BCG | bcg.com | 管理咨询/行业洞察 |
| Bain | bain.com | 管理咨询 |
| Deloitte | deloitte.com | 咨询/行业报告 |
| 艾瑞咨询 | iresearch.cn | 中国互联网/消费研究 |
| 易观分析 | analysys.cn | 中国数字产业分析 |
| IDC | idc.com | IT/电信市场数据 |
| Forrester | forrester.com | 技术市场研究 |
| Bloomberg | bloomberg.com | 财经/市场数据 |
| Reuters | reuters.com | 财经/商业新闻 |

---

## 7. 政策/法规维度

| 来源 | allowed_domains | 适用场景 |
|------|-----------------|----------|
| 中国政府网 | gov.cn | 中国政策/法规/统计 |
| 国家统计局 | stats.gov.cn | 中国官方统计数据 |
| 北大法宝 | pkulaw.com | 中国法律法规检索 |
| 工信部 | miit.gov.cn | 中国产业政策 |
| 国家发改委 | ndrc.gov.cn | 宏观经济政策 |
| 网信办 | cac.gov.cn | 互联网/数据政策 |
| WHO | who.int | 全球卫生政策/数据 |
| World Bank | worldbank.org | 全球经济数据/报告 |
| IMF | imf.org | 全球经济/金融数据 |
| OECD | oecd.org | 发达国家政策/数据 |
| 欧盟法规 | eur-lex.europa.eu | EU 法律/法规 |
| 美国联邦法规 | federalregister.gov | 美国法规 |

---

## 8. 国际对比 / 跨区域视角

| 来源 | allowed_domains | 适用场景 |
|------|-----------------|----------|
| World Bank Open Data | data.worldbank.org | 全球发展指标 |
| OECD Data | data.oecd.org | 发达国家统计数据 |
| Statista | statista.com | 跨国市场数据 |
| Our World in Data | ourworldindata.org | 全球发展数据可视化 |
| UN Data | data.un.org | 联合国统计数据 |
| 各国统计局 | 视具体国家而定 | 官方人口/经济/社会数据 |
| Nikkei Asia | asia.nikkei.com | 亚洲商业/科技 |
| Financial Times | ft.com | 国际财经/商业 |
| The Economist | economist.com | 国际政治经济 |

---

## 使用规则

| 规则 | 说明 |
|------|------|
| 每轮至少 2 个不同来源类型 | 单一来源类型（如全学术或全新闻）不满足多样性要求 |
| 优先高可信来源 | 政府 (.gov)、学术期刊、权威咨询机构优先于行业媒体、个人博客 |
| `allowed_domains` 非强制穷举 | 目标为提升信噪比，非限制搜索范围 — 重要发现可超出本清单 |
| 按主题扩展 | 涉及特定领域时追加该领域权威来源（如金融加 Bloomberg/Reuters，生物医药加 PubMed/Nature） |
| 低可信来源标注 | 来自 Reddit/知乎/V2EX 等社区来源的信息必须在引用时标注「社区来源，未经独立核实」 |
