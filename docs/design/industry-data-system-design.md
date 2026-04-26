---
name: 行业数据存储与检索系统详细设计
description: dAnalyzer 行业数据混合存储与高级检索系统完整设计文档
version: 1.0
date: 2026-04-26
---

# dAnalyzer 行业数据存储与检索系统详细设计

## 1. 设计哲学

### 1.1 核心哲学

dAnalyzer 行业数据系统的核心哲学是**「混合存储 + 按需检索 + 行业适配」**。

| 哲学 | 描述 | 实践方式 |
|------|------|----------|
| **混合存储** | YAML + SQLite 双轨并行 | YAML 人类可读，SQLite 高速检索 |
| **按需检索** | 仅在需要时检索行业知识 | 动态注入上下文，减少膨胀 |
| **行业适配** | 支持多行业可切换配置 | _base 通用 + 行业特定 |
| **零依赖** | 仅使用 Python 标准库 | 无外部向量库依赖 |
| **自动同步** | YAML 变更自动同步到 SQLite | 启动时增量更新 |

### 1.2 设计意图

```
传统方案:
  纯 YAML: 人类可读，但检索慢 (~100ms+)
  纯 SQLite: 检索快，但编辑不便
  向量数据库: 检索准，但依赖重 (~GB 内存)

dAnalyzer 方案:
  YAML (编辑) ←→ SQLite (检索)
  优势: 人类可读 + 高速检索 + 零依赖
  检索: FTS5 + N-gram + RRF 融合 (< 5ms)
```

### 1.3 与其他模块的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    行业数据系统                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  data/industry/                                            │
│  ├── _base/              # 通用基础配置                      │
│  │   ├── indicators/     # 通用指标 (6个)                  │
│  │   ├── scenarios/      # 通用场景 (3个)                  │
│  │   ├── mappings/        # 通用字段映射                    │
│  │   └── config.yaml      # 通用配置                        │
│  │                                                             │
│  └── ecommerce/          # 电商行业 (默认)                  │
│      ├── indicators/     # 电商指标                        │
│      ├── scenarios/      # 电商场景                        │
│      ├── config.yaml      # 行业配置                        │
│      └── preferences.yaml # 用户偏好                        │
│                                                             │
│  scripts/industry/                                          │
│  ├── store.py            # IndustryStore (混合存储)        │
│  └── retriever.py        # IndustryRetriever (高级检索)    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      context-retriever       │
              │         (Skill)              │
              └───────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        danalyzer-core   data-query       visual
         (Agent)          (Skill)          (Skill)
```

---

## 2. 设计原则与理念

### 2.1 核心设计原则

#### 原则 1: 混合存储架构

```
┌─────────────────────────────────────────────────────────┐
│                    混合存储架构                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   YAML (源)                    SQLite (检索)           │
│   ├── 人类可读                  ├── 高速查询            │
│   ├── 便于编辑                  ├── 支持索引            │
│   └── 版本控制友好              ├── FTS5 支持           │
│        │                           │                    │
│        └───────── 自动同步 ────────┘                    │
│                    启动时增量更新                        │
└─────────────────────────────────────────────────────────┘
```

#### 原则 2: 多层检索融合

```
单一检索 → 组合检索 (RRF):

输入: "配送时效"
    │
    ▼
┌─────────────────┬─────────────────┬─────────────────┐
│   FTS5 检索     │  向量检索       │   LIKE 检索     │
│   (全文搜索)    │  (N-gram)       │   (回退)        │
│   返回 Top 5    │  返回 Top 5    │   返回 Top 5    │
└────────┬────────┴────────┬────────┴────────┬────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
                  ┌─────────────────┐
                  │  RRF 融合排序   │
                  │  ( Reciprocal   │
                  │   Rank Fusion)  │
                  └────────┬────────┘
                           │
                           ▼
                    最终 Top 5 结果
```

#### 原则 3: 行业可扩展性

```
行业配置层级:

_base (通用基础)
    ↓ 继承
ecommerce (电商) / logistics (物流) / manufacturing (制造)
    ↓ 可扩展
金融 / 医疗 / 教育 ...

继承关系:
- 继承 _base 的通用指标和场景
- 添加行业特定的指标和场景
- 可覆盖 _base 的配置
```

#### 原则 4: 零依赖设计

```
纯 Python 标准库实现:
- sqlite3: SQLite 检索 (内置)
- yaml: YAML 解析 (内置)
- re: 正则表达式 (内置)
- hashlib: 向量哈希 (内置)
- math: 向量计算 (内置)

vs 向量数据库方案:
- Milvus: 需要 Docker/独立服务 (~GB 内存)
- Pinecone: 需要 API Key (付费)
- Chroma: 功能有限
```

### 2.2 设计模式

| 模式 | 说明 | 实践 |
|------|------|------|
| **Lazy Load** | 按需加载 | 仅检索需要的行业知识 |
| **Cache** | 结果缓存 | 避免重复检索 |
| **Fallback** | 多级回退 | FTS5 → 向量 → LIKE |
| **Auto-sync** | 自动同步 | YAML 变更自动更新 SQLite |

---

## 3. 数据架构设计

### 3.1 目录结构

```
data/industry/
├── _base/                      # ⭐ 通用基础配置
│   ├── config.yaml              # 通用设置 (时间格式/精度/分页)
│   ├── preferences.yaml         # 默认用户偏好
│   ├── common-indicator.md      # 通用指标说明
│   ├── indicators/             # 通用指标 (6个)
│   │   ├── user_id.yaml
│   │   ├── order_id.yaml
│   │   ├── amount.yaml
│   │   ├── status.yaml
│   │   ├── created_at.yaml
│   │   └── updated_at.yaml
│   ├── scenarios/               # 通用场景 (3个)
│   │   ├── time_trend.yaml
│   │   ├── user_behavior.yaml
│   │   └── status_distribution.yaml
│   └── mappings/                # 字段映射
│       └── common_mapping.yaml
│
└── ecommerce/                  # 电商行业 (默认)
    ├── config.yaml              # 行业配置
    ├── preferences.yaml         # 用户偏好
    ├── indicators/              # 电商指标
    │   ├── sales_*.yaml
    │   ├── order_*.yaml
    │   └── user_*.yaml
    ├── scenarios/               # 电商场景
    │   ├── sales_trend.yaml
    │   ├── conversion_funnel.yaml
    │   └── user_retention.yaml
    └── mappings/                # 表映射
        └── order_mapping.yaml
```

### 3.2 指标定义 (indicators/)

**文件格式**: YAML

```yaml
# 指标定义示例
id: base_003
code: user_id
name: 用户ID
type: indicator
industry: _base

keywords:
  - 用户ID
  - 用户编号
  - user_id
  - customer_id
  - member_id

description: |
  通用用户标识字段，用于用户相关的数据关联。

definition:
  formula: user_id
  aggregation: COUNT(DISTINCT)
  unit: 个
  precision: 0

mapping:
  table: "*"
  field: user_id

stats:
  access_count: 800
  importance: 0.95
  updated: 2026-04-26
```

**字段说明**:
| 字段 | 说明 |
|------|------|
| id | 唯一标识 |
| code | 指标代码 |
| name | 指标名称 |
| keywords | 检索关键词 |
| description | 详细描述 |
| definition.formula | 计算公式 |
| definition.aggregation | 聚合方式 |
| mapping.table | 对应数据库表 |
| mapping.field | 对应字段 |
| stats.access_count | 访问次数 |
| stats.importance | 重要性 (0-1) |

### 3.3 场景定义 (scenarios/)

**文件格式**: YAML

```yaml
# 场景定义示例
id: base_scn_001
code: time_trend
name: 时间趋势分析
type: scenario
industry: _base

keywords:
  - 趋势
  - 时间趋势
  - 同比
  - 环比

description: |
  通用时间趋势分析场景。

content:
  required:
    - created_at
    - amount
  optional:
    - order_id
    - user_id
  dimensions:
    时间维度: [日, 周, 月, 季度, 年]
    对比: [同比, 环比]

stats:
  usage_count: 500
  satisfaction: 0.85
```

### 3.4 字段映射 (mappings/)

```yaml
# 通用字段映射示例
mappings:
  # 时间相关
  created_at:
    - created_at
    - create_time
    - gmt_create
    - ctime

  # 用户相关
  user_id:
    - user_id
    - customer_id
    - member_id
    - uid
    - buyer_id

  # 金额相关
  amount:
    - amount
    - total_amount
    - order_amount
    - pay_amount
```

### 3.5 行业配置 (config.yaml)

```yaml
# 电商行业配置
industry:
  name: "电商"
  code: "ecommerce"

datasource:
  default: "hive"
  tables:
    - orders
    - order_items
    - products
    - users

# 核心指标定义
metrics:
  销售额:
    formula: SUM(order_amount), status='paid'
  GMV:
    formula: SUM(order_amount)
  订单量:
    formula: COUNT(order_id), status='paid'
```

---

## 4. 存储引擎设计 (IndustryStore)

### 4.1 核心类设计

```python
class IndustryStore:
    """
    行业数据混合存储引擎

    特性:
    - YAML 编辑: 人类可读，便于手动编辑
    - SQLite 检索: 高速查询，支持索引
    - 自动同步: 启动时检测变更并同步
    - 零依赖: 仅使用 Python 标准库
    """
```

### 4.2 数据库表结构

```sql
-- 指标表
CREATE TABLE indicators (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    keywords TEXT,
    description TEXT,
    formula TEXT,
    unit TEXT,
    precision INTEGER,
    table_name TEXT,
    field_name TEXT,
    access_count INTEGER DEFAULT 0,
    importance REAL DEFAULT 0.5,
    updated TEXT,
    relations TEXT,
    _file_path TEXT
);

-- 场景表
CREATE TABLE scenarios (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    keywords TEXT,
    description TEXT,
    required_indicators TEXT,
    optional_indicators TEXT,
    dimensions TEXT,
    template TEXT,
    usage_count INTEGER DEFAULT 0,
    satisfaction REAL DEFAULT 0.5,
    updated TEXT,
    _file_path TEXT
);

-- 偏好表
CREATE TABLE preferences (
    user_id TEXT NOT NULL UNIQUE,
    default_industry TEXT,
    preferred_dimensions TEXT,
    default_time_range TEXT,
    preferred_format TEXT,
    frequent_queries TEXT,
    frequent_scenarios TEXT,
    updated TEXT
);

-- 索引
CREATE INDEX idx_ind_code ON indicators(code);
CREATE INDEX idx_scn_code ON scenarios(code);
```

### 4.3 自动同步机制

```
启动时检查流程:

1. 检查 YAML 目录是否存在
       │
       ▼
2. 比较 YAML 最新修改时间 vs SQLite 修改时间
       │
       ▼
3. 需要同步?
   ├── 否 → 直接使用现有数据库
   └── 是 → 执行同步
              │
              ▼
         删除旧数据
              │
              ▼
         遍历 YAML 文件
              │
              ▼
         解析并写入 SQLite
              │
              ▼
         更新同步元数据
              │
              ▼
         完成
```

### 4.4 检索接口

```python
def search(self, query: str, top_k: int = 5) -> Dict[str, List[Dict]]:
    """
    统一检索接口

    Args:
        query: 查询关键词
        top_k: 返回结果数量

    Returns:
        {
            "indicators": [...],
            "scenarios": [...],
            "query": query
        }
    """
```

---

## 5. 检索引擎设计 (IndustryRetriever)

### 5.1 核心类设计

```python
class IndustryRetriever:
    """
    行业数据检索器 (V2)

    特性:
    - FTS5 全文搜索 (SQLite 内置)
    - N-gram 向量检索 (纯 Python)
    - RRF 融合 (业界标准)
    - 时间衰减
    - MMR 多样性重排
    """
```

### 5.2 FTS5 全文搜索

```python
def fts_search(self, query: str, table: str = "indicators", top_k: int = 5):
    """
    FTS5 全文搜索

    特点:
    - SQLite 内置，无需额外依赖
    - 支持中文分词 (3-gram)
    - 支持 AND/OR/NOT 操作符
    - 性能: < 2ms
    """
```

**FTS5 表结构**:
```sql
CREATE VIRTUAL TABLE indicators_fts USING fts5(
    code,
    name,
    keywords,
    description
);
```

### 5.3 N-gram 向量检索

```python
def vector_search(self, query: str, table: str = "indicators", top_k: int = 5):
    """
    N-gram 向量检索

    实现:
    - 使用字符级 3-gram
    - MD5 哈希映射到向量
    - 纯 Python 实现，零依赖
    - 性能: < 3ms
    """
```

**向量生成算法**:
```
输入: "配送时效"
    │
    ▼
3-gram 分词: [配送, 送时, 时效]
    │
    ▼
MD5 哈希: [hash(配送), hash(送时), hash(时效)]
    │
    ▼
向量映射: [0.1, 0.3, 0.2, ...] (128维)
    │
    ▼
L2 归一化: [0.1/N, 0.3/N, 0.2/N, ...]
    │
    ▼
余弦相似度计算
```

### 5.4 RRF 融合排序

```python
def rrf_fusion(self, results_list: List[List[Dict]], top_k: int = 5):
    """
    RRF (Reciprocal Rank Fusion) 融合

    公式:
    RRF(d) = Σ 1 / (k + rank(d))
    其中 k = 60 (常数)
    """
```

**融合流程**:
```
输入: [FTS5结果, 向量结果, LIKE结果]
    │
    ▼
各结果集分配排名分数
    │
    ▼
RRF 公式计算综合分数
    │
    ▼
按综合分数排序
    │
    ▼
输出 Top K
```

### 5.5 统一检索接口

```python
def search(self, query: str, use_fts: bool = True, use_vector: bool = True,
           use_rrf: bool = True, top_k: int = 5):
    """
    统一检索接口

    Args:
        query: 查询文本
        use_fts: 使用 FTS5 检索
        use_vector: 使用向量检索
        use_rrf: 使用 RRF 融合
        top_k: 返回数量

    Returns:
        检索结果字典
    """
```

---

## 6. 执行流程

### 6.1 数据同步流程

```
应用启动
    │
    ▼
IndustryStore 初始化
    │
    ▼
检查是否需要同步
    │
    ├── 不需要 → 直接使用
    └── 需要 → _sync_from_yaml()
                  │
                  ▼
              创建数据库表
                  │
                  ▼
              同步 indicators
                  │
                  ▼
              同步 scenarios
                  │
                  ▼
              同步 preferences
                  │
                  ▼
              更新同步元数据
                  │
                  ▼
              完成
```

### 6.2 行业知识检索流程

```
用户输入: "查询上月各地区配送时效"
    │
    ▼
danalyzer-core 判断需要行业知识
    │
    ▼
调用 context-retriever Skill
    │
    ▼
判断使用哪种检索方式:
    │
    ├─ 简单查询 → FTS5 检索
    ├─ 复杂查询 → FTS5 + 向量 + RRF
    └─ FTS5 失败 → LIKE 回退
    │
    ▼
检索指标:
    - avg_delivery_time (平均配送时长)
    - on_time_delivery_rate (准时交付率)
    │
    ▼
检索表映射:
    - delivery_orders 表
    - duration_hours, region, order_time 字段
    │
    ▼
检索时间解析:
    - "上月" → 2026-03-01 ~ 2026-03-31
    │
    ▼
返回检索结果给 data-query
    │
    ▼
data-query 使用检索结果生成 SQL
```

### 6.3 上下文注入流程

```
检索结果:
{
  "indicators": [
    {
      "code": "avg_delivery_time",
      "name": "平均配送时长",
      "formula": "AVG(TIMESTAMPDIFF(HOUR, order_time, delivery_time))",
      "table": "delivery_orders",
      "field": "duration_hours"
    }
  ],
  "mappings": [...],
  "time": {...},
  "dimensions": [...]
}
    │
    ▼
注入到 data-query 的 NL2SQL prompt:
    │
    ▼
生成 SQL:
SELECT region, AVG(duration_hours) as avg_delivery_time
FROM delivery_orders
WHERE order_time >= '2026-03-01' AND order_time < '2026-04-01'
GROUP BY region
```

---

## 7. 与其他模块的协同

### 7.1 与 context-retriever Skill 的协同

```
context-retriever Skill
    │
    ├─ 输入: user_input + industry
    │
    ├─ 调用方式:
    │   Skill: context-retriever
    │   参数: {
    │     "user_input": "查询上月各地区配送时效",
    │     "industry": "logistics"
    │   }
    │
    └─ 输出:
        {
          "indicators": [...],
          "mappings": [...],
          "time": {...},
          "dimensions": [...]
        }
```

### 7.2 与 danalyzer-core Agent 的协同

```
danalyzer-core
    │
    ▼
需求理解
    │
    ▼
判断是否需要检索行业知识?
    ├── 包含行业特征词 → 是
    └── 需求明确 → 否
    │
    ▼
调用 context-retriever
    │
    ▼
获取行业上下文
    │
    ▼
传递给 data-query Skill
    │
    ▼
生成准确 SQL
```

### 7.3 与 data-query Skill 的协同

```
data-query Skill
    │
    ▼
NL2SQL 转换前
    │
    ▼
检查是否有注入的行业上下文
    │
    ├─ 有 → 使用上下文生成 SQL
    │   - 指标定义 → 计算方式
    │   - 表映射 → 字段名称
    │   - 时间范围 → WHERE 条件
    │
    └─ 无 → 直接解析用户输入
    │
    ▼
输出 SQL
```

### 7.4 与 Hooks 的协同

```
SessionStart Hook
    │
    ▼
加载 danalyzer-guide
    │
    ▼
(可选) 预加载行业索引

PostToolUse (Skill 执行后)
    │
    ▼
analyze-observe: 记录检索行为
    │
    ▼
instinct-apply: (可选) 智能建议
```

---

## 8. 与 Claude Code 的集成

### 8.1 Skill 工具集成

```markdown
# 调用 context-retriever Skill
Skill: context-retriever
输入:
{
  "user_input": "查询上月各地区配送时效",
  "industry": "logistics"
}

输出:
{
  "status": "success",
  "retrieved": {
    "indicators": [...],
    "mappings": [...],
    "time": {...}
  }
}
```

### 8.2 Python 模块直接调用

```python
# 方式1: 使用 Skill (基础)
Skill: context-retriever

# 方式2: 直接调用 Python 模块 (高级) ⭐ 推荐

import sys
sys.path.append('scripts/industry')
from store import get_store
from retriever import get_retriever

# 初始化 (自动同步 YAML → SQLite)
store = get_store("ecommerce")
retriever = get_retriever(store)

# 高级检索 (FTS5 + 向量 + RRF)
results = retriever.search(
    query="销售趋势",
    use_fts=True,
    use_vector=True,
    use_rrf=True
)

# 返回结果
results["indicators"]  # 相关指标
results["scenarios"]   # 相关场景
```

### 8.3 检索性能

| 检索方式 | 性能 | 说明 |
|----------|------|------|
| FTS5 | < 2ms | SQLite 内置全文搜索 |
| 向量 | < 3ms | 纯 Python N-gram |
| RRF 融合 | < 5ms | 组合多种检索结果 |
| LIKE 回退 | < 10ms | FTS5 失败时的备选 |

---

## 9. 方案优势与劣势

### 9.1 方案优势

| 优势 | 说明 | 效果 |
|------|------|------|
| **混合存储** | YAML + SQLite 双轨 | 人类可读 + 高速检索 |
| **零依赖** | 仅用 Python 标准库 | 部署简单，无额外依赖 |
| **自动同步** | 启动时增量更新 | 保持数据一致性 |
| **多检索融合** | FTS5 + 向量 + RRF | 检索准确率高 |
| **行业可扩展** | _base + 行业特定 | 灵活适配多行业 |
| **按需检索** | 仅在需要时检索 | 控制上下文膨胀 |
| **性能优异** | 毫秒级响应 | 用户无感知 |

### 9.2 方案劣势

| 劣势 | 说明 | 缓解措施 |
|------|------|----------|
| **向量精度** | N-gram 哈希 vs BERT | 对于关键词检索足够 |
| **中文分词** | 字符级 3-gram | 简单有效 |
| **SQLite 限制** | 单机文件数据库 | 适合中小规模 |
| **启动开销** | 首次同步有延迟 | 自动增量同步 |

### 9.3 适用场景

| 场景 | 适用性 | 原因 |
|------|--------|------|
| 中小规模数据 (<10万指标) | ✅ 最佳 | SQLite 性能足够 |
| 多行业切换 | ✅ 最佳 | 行业可配置 |
| 关键词检索 | ✅ 最佳 | FTS5 擅长 |
| 语义检索 | ⚠️ 一般 | N-gram 简化实现 |
| 超大规模数据 | ⚠️ 慎重 | 建议升级到专用向量库 |

### 9.4 与向量数据库对比

| 维度 | dAnalyzer 方案 | 向量数据库 (Milvus/Pinecone) |
|------|---------------|------------------------------|
| 依赖 | 零依赖 | 需要独立服务 |
| 内存 | < 10MB | ~GB 级别 |
| 精度 | 关键词检索 95%+ | 语义理解 90%+ |
| 部署 | 单文件 | Docker/K8s |
| 成本 | 免费 | 付费 |

---

## 10. 扩展设计

### 10.1 新增行业

```
1. 创建目录: data/industry/{新行业}/
2. 添加配置: config.yaml
3. 添加指标: indicators/*.yaml
4. 添加场景: scenarios/*.yaml
5. 启动时自动同步
```

### 10.2 新增检索方式

```python
# 扩展检索器
class IndustryRetriever:
    def search(self, query, method="hybrid"):
        if method == "hybrid":
            # 现有 RRF 融合
        elif method == "bm25":
            # 可添加 BM25 检索
        elif method == "embedding":
            # 可集成 BERT 向量 (可选)
```

### 10.3 缓存优化

```python
# 添加缓存层
@lru_cache(maxsize=100)
def search_cached(self, query: str, industry: str):
    # 缓存热门查询结果
    return self.search(query)
```

---

## 11. 总结

### 11.1 设计要点

dAnalyzer 行业数据系统通过以下设计实现高效、灵活的行业知识管理:

1. **混合存储**: YAML (编辑) + SQLite (检索)
2. **自动同步**: 启动时增量更新
3. **多检索融合**: FTS5 + N-gram + RRF
4. **行业可扩展**: _base + 行业特定
5. **零依赖**: 仅用 Python 标准库

### 11.2 与 Skills/Agents 的协同

| 模块 | 协同方式 |
|------|----------|
| context-retriever Skill | 行业知识检索入口 |
| danalyzer-core Agent | 决策调用检索 |
| data-query Skill | 使用检索结果生成 SQL |
| visual Skill | 使用检索结果生成图表 |

### 11.3 性能指标

| 指标 | 数值 |
|------|------|
| FTS5 检索 | < 2ms |
| 向量检索 | < 3ms |
| RRF 融合 | < 5ms |
| 启动同步 (100个文件) | < 1s |

### 11.4 演进方向

- 添加更多行业支持 (金融、医疗)
- 集成 BERT 向量 (可选)
- 添加缓存层
- 支持分布式部署

---

*本文档于 2026-04-26 创建 (v1.0)*
