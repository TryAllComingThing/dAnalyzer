# dAnalyzer Core — 分析参考附录

> 按需读取，非每次加载。核心编排流程见 SKILL.md。
> **Phase 1:** 意图→场景→模型的结构化路由已移至 `knowledge/intent-routing.yaml`。本文档保留技能链与图表选型参考。

---

## 一、分析类型决策

根据用户需求选择分析深度：

### 描述性分析 — "发生了什么"
**适用：** 查询指标、看趋势、日报周报、简单统计
**输出：** 数据表格 + 趋势图/柱状图
**链路：** data-query → data-analysis → visual → security

### 诊断性分析 — "为什么发生"
**适用：** 异动归因、对比分析、下钻分析
**输出：** 归因结论 + 对比图表 + 数据表
**链路：** data-query → data-clean → data-analysis → model(attribution) → visual → report → security

### 预测性分析 — "将会发生什么"
**适用：** 趋势预测、留存预测、销量预估
**输出：** 预测曲线 + 置信区间 + 数据表
**链路：** data-query → data-clean → model(forecasting) → visual → security

### 规范性分析 — "应该怎么做"
**适用：** 策略建议、优化方案、资源分配
**输出：** 建议报告 + 对比方案 + 可视化
**链路：** data-query → data-clean → data-analysis → model → visual → report → security

### 探索性分析 — "数据告诉我们什么"
**适用：** 新数据集探索、聚类发现、相关性挖掘
**输出：** 探索报告 + 多维图表
**链路：** data-query → data-clean → data-analysis → model(clustering/correlation) → visual → insight-gen → security

---

## 二、技能编排参考

### 通用技能链

| 需求 | 技能组合 |
|------|----------|
| 销售周报 | data-query → data-clean → data-analysis → visual → report → security |
| 用户RFM | data-query → model(rfm) → visual → security |
| 合规导出 | data-query → compliance → security |
| 简单查询 | data-query → security |
| 漏斗分析 | data-query → model(funnel) → visual → security |
| 复杂分析 | data-query → data-clean → data-analysis → model → visual → security |
| 看板生成 | data-query → data-analysis → dashboard → security |

### 子技能映射

| 用户需求关键词 | 主 Skill | 子技能文件 |
|---------------|----------|-----------|
| RFM、用户价值、用户分层 | model | references/rfm-analysis.md |
| 漏斗、转化、流失路径 | model | references/funnel-analysis.md |
| 聚类、分群、用户画像 | model | references/clustering.md |
| 归因、渠道贡献 | model | references/attribution.md |
| 预测、趋势预判 | model | references/forecasting.md |
| 留存、同期群 | model | references/cohort-analysis.md |
| 相关系数、变量关系 | model | references/correlation-analysis.md |

### 可用 Skills

| 类别 | Skills |
|------|--------|
| 数据查询 | data-query |
| 数据处理 | data-clean |
| 数据分析 | data-analysis, model |
| 输出 | visual, report, dashboard |
| 安全 | security |
| 辅助 | context-retriever, insight-gen |

---

## 三、图表选型指南

| 分析意图 | 推荐图表 | 说明 |
|---------|---------|------|
| 趋势变化 | 折线图 | 时间序列数据 |
| 占比构成 | 饼图/环形图/堆叠柱状图 | 类别占比 |
| 对比排序 | 柱状图/条形图 | 多类别对比 |
| 分布情况 | 直方图/箱线图 | 数据分布 |
| 相关性 | 散点图 | 两变量关系 |
| 地理分布 | 地图 | 区域数据 |
| 指标总览 | 仪表盘/卡片 | 关键指标汇总 |
| 转化路径 | 漏斗图 | 转化分析 |
| 多维度对比 | 雷达图 | 多维度对比 |
