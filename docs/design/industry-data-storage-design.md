# dAnalyzer 行业数据存储与检索方案

> 版本: 3.0 (2026-04-26)
> 设计理念: 三层记忆 + SQLite 存储 + 混合检索 + RRF融合
> 评审优化: AI 技术专家评审后改进 + 最佳实践

---

## 一、设计背景

dAnalyzer 需要一套行业数据存储与检索机制，用于：
- **指标定义**: 什么字段、计算公式
- **业务场景**: 分析模板、常用套路
- **用户偏好**: 历史查询、常用设置

核心要求：
- **按需加载**: 不一次性加载全部数据
- **高效检索**: 检索延迟 < 50ms
- **易于编辑**: YAML 用于编辑，SQLite 用于检索
- **自动同步**: YAML 变更自动同步到 SQLite

---

## 二、核心概念：三层记忆

| 层级 | 定义 | 存储内容 | 存储位置 |
|------|------|----------|----------|
| **Semantic (语义)** | 事实性知识 | 指标定义、字段映射、概念 | SQLite: `indicators` 表 |
| **Episodic (情景)** | 模式性知识 | 分析场景、模板、套路 | SQLite: `scenarios` 表 |
| **Working (工作)** | 动态性知识 | 用户偏好、历史查询 | SQLite: `preferences` 表 |

```
用户查询 "查本月销售额趋势"
    │
    ├──▶ Semantic: 找到 "销售额" 指标定义
    ├──▶ Episodic: 找到 "销售趋势分析" 场景
    └──▶ Working: 找到用户常用的 "本月" 时间范围
```

---

## 三、存储架构 (最佳实践)

### 3.1 混合存储设计

```
┌─────────────────────────────────────────────────────────────┐
│                      混合存储架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   编辑层 (YAML)              存储层 (SQLite)                 │
│   ┌─────────────┐          ┌─────────────┐                 │
│   │ indicators/ │  ─────▶  │  indicators │                 │
│   │ scenarios/  │  自动同步 │  scenarios  │                 │
│   │ preferences │          │  preferences│                 │
│   └─────────────┘          └─────────────┘                 │
│         │                        │                          │
│         │                        ▼                          │
│         │                  ┌─────────────┐                 │
│         │                  │  SQLite DB  │                 │
│         │                  │  (单文件)   │                 │
│         │                  └─────────────┘                 │
│         │                        │                          │
│         └────────────────────────┘                          │
│                          │                                   │
│                          ▼                                   │
│                      检索层 (内存)                          │
│                      (< 50ms 查询)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 目录结构

```
knowledge/industry/
├── _base/                          # 通用基础 (所有行业继承)
│   ├── _base.db                    # SQLite 数据库 (自动生成)
│   ├── indicators/                 # YAML: 通用指标
│   │   ├── _index.yaml
│   │   └── ...
│   ├── scenarios/                 # YAML: 通用场景
│   └── mappings/
│
├── ecommerce/                      # 电商 (覆盖_base)
│   ├── ecommerce.db                # ⭐ SQLite 数据库
│   ├── indicators/                # ⭐ 仅用于编辑
│   │   ├── sales_amount.yaml
│   │   ├── order_count.yaml
│   │   └── conversion_rate.yaml
│   │
│   ├── scenarios/                 # ⭐ 仅用于编辑
│   │   ├── sales_trend.yaml
│   │   └── user_analysis.yaml
│   │
│   ├── mappings/
│   │   └── table_mappings.yaml
│   │
│   └── preferences.yaml            # ⭐ 仅用于编辑
│
├── logistics/                     # 物流
│   ├── logistics.db
│   └── ...
│
├── manufacturing/                 # 制造
└── finance/                       # 金融
```

---

## 四、SQLite 数据库设计

### 4.1 表结构设计

> **重要**: SQLite 是嵌入式数据库，零依赖，Python 自带 `sqlite3` 模块，单文件存储，复制即走，与 YAML 一样绿色。

#### 4.1.1 语义层: 指标表 (indicators)

```sql
CREATE TABLE indicators (
    -- 基础信息
    id          TEXT PRIMARY KEY,           -- ind_001
    code        TEXT NOT NULL,              -- sales_amount
    name        TEXT NOT NULL,              -- 销售额
    industry    TEXT,                      -- ecommerce
    
    -- 检索字段
    keywords    TEXT,                       -- JSON: ["销售","营收","GMV"]
    description TEXT,                      -- 详细描述
    
    -- 指标定义
    formula     TEXT,                      -- SUM(order_amount - refund)
    unit        TEXT,                      -- 元
    precision   INTEGER,                   -- 2
    table_name  TEXT,                      -- orders
    field_name  TEXT,                      -- order_amount
    
    -- 统计 (用于排序)
    access_count INTEGER DEFAULT 0,
    importance   REAL DEFAULT 0.5,
    updated      TEXT,                      -- 2026-04-26
    
    -- 关系
    relations   TEXT                       -- JSON: {children: [], parents: []}
);

-- 索引
CREATE INDEX idx_ind_code ON indicators(code);
CREATE INDEX idx_ind_keywords ON indicators(keywords);  -- JSON 字段
CREATE INDEX idx_ind_importance ON indicators(importance DESC);
CREATE INDEX idx_ind_access ON indicators(access_count DESC);
```

#### 4.1.2 情景层: 场景表 (scenarios)

```sql
CREATE TABLE scenarios (
    -- 基础信息
    id          TEXT PRIMARY KEY,           -- scn_001
    code        TEXT NOT NULL,              -- sales_trend
    name        TEXT NOT NULL,              -- 销售趋势分析
    industry    TEXT,
    
    -- 检索字段
    keywords    TEXT,                       -- JSON: ["趋势","同比","环比"]
    description TEXT,                      -- 场景描述
    
    -- 场景内容
    required_indicators TEXT,              -- JSON: ["sales_amount"]
    optional_indicators TEXT,              -- JSON: ["avg_order_value"]
    dimensions  TEXT,                      -- JSON: {"时间维度":["日","周","月"]}
    template    TEXT,                      -- JSON: {sections: []}
    
    -- 统计
    usage_count INTEGER DEFAULT 0,
    satisfaction REAL DEFAULT 0.5,
    updated      TEXT
);

-- 索引
CREATE INDEX idx_scn_code ON scenarios(code);
CREATE INDEX idx_scn_keywords ON scenarios(keywords);
CREATE INDEX idx_scn_satisfaction ON scenarios(satisfaction DESC);
```

#### 4.1.3 工作层: 偏好表 (preferences)

```sql
CREATE TABLE preferences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL UNIQUE,       -- user_001
    
    -- 偏好设置
    default_industry TEXT,                  -- ecommerce
    preferred_dimensions TEXT,              -- JSON: ["区域","类目"]
    default_time_range TEXT,               -- 本月
    preferred_format TEXT,                 -- chart
    
    -- 历史记录 (用于推荐)
    frequent_queries TEXT,                  -- JSON: [{query, count}]
    frequent_scenarios TEXT,                -- JSON: [{code, count}]
    
    updated      TEXT
);

-- 索引
CREATE INDEX idx_prefs_user ON preferences(user_id);
```

#### 4.1.4 系统表: 同步元数据 (sync_meta)

```sql
CREATE TABLE sync_meta (
    table_name  TEXT PRIMARY KEY,
    last_sync   TEXT,                       -- 2026-04-26 10:00:00
    record_count INTEGER,
    file_hash   TEXT                        -- YAML 文件 hash，用于检测变更
);
```

### 4.2 ER 图

```
┌─────────────────────────────────────────────────────────────┐
│                    knowledge/industry/ecommerce.db               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────┐    ┌────────────────┐                   │
│  │  indicators   │    │   scenarios    │                   │
│  │  (语义层)      │    │  (情景层)      │                   │
│  ├────────────────┤    ├────────────────┤                   │
│  │ id (PK)        │    │ id (PK)        │                   │
│  │ code (idx)     │    │ code (idx)     │                   │
│  │ name           │    │ name           │                   │
│  │ keywords(idx) │    │ keywords(idx)  │                   │
│  │ description   │    │ description    │                   │
│  │ formula       │    │ template       │                   │
│  │ importance   │    │ satisfaction   │                   │
│  │ access_count │    │ usage_count    │                   │
│  └────────────────┘    └────────────────┘                   │
│          │                       │                          │
│          │                       │                          │
│  ┌────────────────┐    ┌────────────────┐                 │
│  │  preferences   │    │   sync_meta    │                  │
│  │  (工作层)       │    │  (系统)         │                 │
│  ├────────────────┤    ├────────────────┤                 │
│  │ id (PK)        │    │ table_name(PK) │                 │
│  │ user_id (idx)  │    │ last_sync      │                 │
│  │ preferences   │    │ file_hash      │                 │
│  │ history       │    │ record_count   │                 │
│  └────────────────┘    └────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、YAML 与 SQLite 自动同步方案

### 5.1 同步策略

| 策略 | 触发时机 | 优点 | 缺点 |
|------|----------|------|------|
| **启动同步** | 应用启动时 | 简单可靠 | 启动稍慢 |
| **文件监控** | YAML 变更时 | 实时 | 需要后台进程 |
| **懒加载** | 首次查询时 | 启动最快 | 首次查询慢 |

**推荐**: 启动同步 + 文件变更检测 (最佳平衡)

### 5.2 同步流程

```
启动流程:
┌─────────────────────────────────────────────────────────────┐
│ 1. 检查 SQLite 是否存在                                      │
│    │                                                         │
│    ├── 不存在 ──▶ 创建数据库 + 执行完整同步                   │
│    │                                                         │
│    └── 存在 ──▶ 检查 YAML 是否有更新                          │
│              │                                               │
│              ├── 有更新 ──▶ 增量/全量同步                     │
│              │                                               │
│              └── 无更新 ──▶ 直接使用缓存                      │
│                                                             │
│ 2. 初始化完成，使用 SQLite 检索                               │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 变更检测

```python
# 使用文件修改时间 + hash 检测变更
def _needs_sync(db_path: Path, yaml_path: Path) -> bool:
    # 检查数据库文件修改时间
    db_mtime = db_path.stat().st_mtime if db_path.exists() else 0
    
    # 检查 YAML 目录最新修改时间
    yaml_mtime = max(
        f.stat().st_mtime 
        for f in yaml_path.rglob("*.yaml")
        if not f.name.startswith("_")
    ) if yaml_path.exists() else 0
    
    return yaml_mtime > db_mtime
```

### 5.4 同步实现

```python
class IndustryStore:
    """混合存储引擎: YAML 编辑 + SQLite 检索"""
    
    def __init__(self, industry: str, data_root: str = "knowledge/industry"):
        self.industry = industry
        self.data_root = Path(data_root)
        self.yaml_path = self.data_root / industry
        self.db_path = self.data_root / f"{industry}.db"
        
        # 启动时自动同步
        self._ensure_init()
    
    def _ensure_init(self):
        """确保数据库初始化"""
        if not self.db_path.exists() or self._needs_sync():
            self._sync_from_yaml()
    
    def _sync_from_yaml(self):
        """从 YAML 同步到 SQLite"""
        conn = sqlite3.connect(self.db_path)
        
        # 创建表
        self._create_tables(conn)
        
        # 同步数据
        self._sync_indicators(conn)
        self._sync_scenarios(conn)
        self._sync_preferences(conn)
        
        # 更新同步元数据
        self._update_sync_meta(conn)
        
        conn.commit()
        conn.close()
```

---

## 六、检索算法 (V2)

### 6.1 整体流程

```
用户查询: "查本月销售额趋势"
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: SQLite 查询 (< 10ms)                               │
│                                                         │
│  - 使用索引快速定位                                       │
│  - 多条件组合查询                                         │
│  - 排序: importance + access_count                       │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 多路检索 (可选)                                    │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ BM25 检索      │  │ N-gram 向量检索  │               │
│  │ (关键词匹配)    │  │ (语义相似)       │               │
│  └────────┬────────┘  └────────┬────────┘               │
│           │                    │                         │
│           └────────┬───────────┘                         │
│                    ▼                                      │
│           ┌─────────────────┐                            │
│           │ 规则检索        │                            │
│           │ 固定关键词映射  │                            │
│           └─────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: RRF 融合 (可选)                                    │
│                                                         │
│  score(doc) = Σ 1/(k + rank_i(doc))                      │
│                                                          │
│  k = 60 (标准值)                                         │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 重排                                              │
│                                                         │
│  1. 时间衰减 (越新越重要)                                 │
│  2. MMR重排 (保持多样性) - 可选                           │
│  3. 返回Top-K                                            │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 性能指标

```
数据规模: 50 个指标 + 20 个场景

┌──────────────────┬──────────────┬──────────────┐
│ 方案             │ 加载         │ 检索         │
├──────────────────┼──────────────┼──────────────┤
│ YAML (当前)      │ 200-500ms    │ 50-100ms     │
│ YAML + 索引      │ 200-500ms    │ 10-20ms      │
│ SQLite          │ 5-10ms       │ 2-5ms        │
│ SQLite + FTS5   │ 5-10ms       │ < 2ms        │
└──────────────────┴──────────────┴──────────────┘
```

---

## 七、性能优化方向

### 7.1 Phase 1: 基础优化 (立即)

- [ ] 实现 SQLite 混合存储
- [ ] 实现 YAML → SQLite 自动同步
- [ ] 添加基础索引
- [ ] 性能测试 (目标: < 50ms)

### 7.2 Phase 2: 全文搜索 (短期)

```sql
-- 使用 SQLite FTS5 全文搜索
CREATE VIRTUAL TABLE indicators_fts USING fts5(
    name,
    keywords,
    description,
    content=indicators,
    content_rowid=rowid
);

-- 查询示例
SELECT indicators.* FROM indicators
JOIN indicators_fts ON indicators.rowid = indicators_fts.rowid
WHERE indicators_fts MATCH '销售 AND 趋势'
ORDER BY rank;
```

**优势**:
- 全文索引，检索更快
- 支持 AND/OR/NOT 语法
- 相关性排序

### 7.3 Phase 3: 向量检索 (中期)

```python
# 方案 A: 轻量级 - N-gram hash
def _ngram_vector(text: str) -> list[float]:
    """字符级 n-gram 向量"""
    ngrams = [text[i:i+3] for i in range(len(text)-2)]
    vec = [0.0] * 128
    for ngram in ngrams:
        h = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
        for i in range(8):
            vec[i*16 + (h >> (i*4)) % 16] += 1.0
    return [v / (sum(v*v)**0.5 or 1) for v in vec]

# 方案 B: 进阶 - sentence-transformers (可选)
# 需要 pip install sentence-transformers
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(['text'])
```

### 7.4 Phase 4: 缓存层 (长期)

```python
from functools import lru_cache

class IndustryStore:
    @lru_cache(maxsize=128)
    def search_cached(self, query: str, top_k: int = 5):
        """带缓存的检索"""
        return self.search(query, top_k)
    
    def invalidate_cache(self):
        """失效缓存"""
        self.search_cached.cache_clear()
```

### 7.5 优化路线图

```
v3.0 (当前)     v3.1          v3.2          v3.3
    │            │             │             │
    ▼            ▼             ▼             ▼
 SQLite       SQLite        SQLite        SQLite
 基础检索    + FTS5        + 向量        + LRU
                           检索         缓存
                           
目标:          目标:         目标:        目标:
< 50ms        < 20ms        < 30ms       < 10ms
```

---

## 八、文件格式

### 8.1 YAML 格式 (用于编辑)

#### 指标定义 (indicators/sales_amount.yaml)

```yaml
# ==================== 基础信息 ====================
id: ind_001
code: sales_amount
name: 销售额
type: indicator
industry: ecommerce

# ==================== 检索字段 ====================
keywords:
  - 销售
  - 营收
  - GMV
  - revenue

description: |
  电商核心指标，表示订单实付金额总和。
  计算公式: SUM(order_amount - refund_amount)

# ==================== 指标定义 ====================
definition:
  formula: SUM(order_amount - refund_amount)
  aggregation: SUM
  unit: 元
  precision: 2

# ==================== 字段映射 ====================
mapping:
  table: orders
  field: order_amount
  joins:
    - table: refunds
      type: left
      on: orders.id = refunds.order_id

# ==================== 统计 ====================
stats:
  access_count: 1250
  importance: 0.95
  updated: 2026-04-26
```

#### 场景定义 (scenarios/sales_trend.yaml)

```yaml
id: scn_001
code: sales_trend
name: 销售趋势分析
type: scenario
industry: ecommerce

keywords:
  - 销售趋势
  - 趋势
  - 同比
  - 环比

description: |
  销售数据的时间趋势分析，包含:
  - 销售额/量趋势
  - 环比同比对比
  - 异常检测

content:
  required:
    - sales_amount
    - order_count
  optional:
    - avg_order_value
    - growth_rate_mom
  dimensions:
    时间维度: [日, 周, 月, 季度, 年]
    区域维度: [全国, 区域, 省份]

stats:
  usage_count: 320
  satisfaction: 0.88
  updated: 2026-04-26
```

#### 用户偏好 (preferences.yaml)

```yaml
user: default

preferences:
  default_industry: ecommerce
  preferred_dimensions: [区域, 类目]
  default_time_range: 本月
  preferred_format: chart

frequent_queries:
  - query: 销售额
    count: 45

frequent_scenarios:
  - code: sales_trend
    count: 18

updated: 2026-04-26
```

### 8.2 SQLite 表 (自动生成)

> SQLite 表由系统自动从 YAML 同步生成，无需手动管理。

---

## 九、实施计划

### Phase 1: 核心功能 (立即)
- [ ] 实现 IndustryStore 混合存储类
- [ ] 实现 YAML → SQLite 自动同步
- [ ] 实现基础 SQLite 检索
- [ ] 性能测试

### Phase 2: 优化 (短期)
- [ ] 添加 FTS5 全文搜索
- [ ] 添加 N-gram 向量检索
- [ ] 添加 RRF 融合

### Phase 3: 完善 (中期)
- [ ] 添加 LRU 缓存
- [ ] 添加时间衰减
- [ ] 添加 MMR 多样性重排

### Phase 4: 集成 (长期)
- [ ] 与 danalyzer-core 集成
- [ ] 与学习系统联动

---

## 十、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v3.0 | 2026-04-26 | 最佳实践版: SQLite 混合存储 + 自动同步 + 优化方向 |
| v2.0 | 2026-04-26 | AI评审优化: BM25 + N-gram hash + RRF |
| v1.0 | 2026-04-25 | 初始版本 |

---

## 十一、参考资源

- [SQLite 官方文档](https://www.sqlite.org/docs.html)
- [SQLite FTS5 全文搜索](https://www.sqlite.org/fts5.html)
- [BM25 算法](https://en.wikipedia.org/wiki/Okapi_BM25)
- [RRF 融合算法](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [vector-memory-hack (轻量级向量搜索)](https://github.com/mig6671/vector-memory-hack)
- [rag-engine (混合 RAG 引擎)](https://github.com/ForwardCodeSolutions/rag-engine)

---

*方案版本: 3.0 (最佳实践)*
*设计参考: 业界最佳实践 + AI 技术专家评审*
*最后更新: 2026-04-26*
