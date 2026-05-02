# Connectors 系统详细设计文档

> 版本: 1.0
> 创建日期: 2026-04-26
> 设计目标: 详细阐述数据连接器系统的设计哲学、架构模式、执行流程与协同机制

---

## 1 设计哲学

### 1.1 核心设计理念

Connectors 系统采用**统一抽象 + 多源适配**的设计哲学，通过定义标准化的接口抽象，屏蔽底层数据源的差异性，让上层业务逻辑无需关心数据来源。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Connectors 设计金字塔                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                      ┌─────────────────────┐                       │
│                      │   业务层 (Skills)    │                       │
│                      │   data-query        │                       │
│                      │   data-clean        │                       │
│                      │   data-analysis    │                       │
│                      └──────────┬──────────┘                       │
│                                 │                                    │
│                                 ▼                                    │
│                      ┌─────────────────────┐                       │
│                      │   连接器抽象层      │                       │
│                      │   BaseConnector     │                       │
│                      │   BaseFileConnector │                       │
│                      └──────────┬──────────┘                       │
│                                 │                                    │
│           ┌─────────────────────┼─────────────────────┐            │
│           │                     │                     │            │
│           ▼                     ▼                     ▼            │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │   MySQL         │   │  ClickHouse    │   │    Oracle       │  │
│  │   PostgreSQL   │   │   (OLAP)       │   │    (RDBMS)      │  │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘  │
│                                                                     │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │   CSV           │   │   JSON          │   │    Excel        │  │
│  │   (Flat File)  │   │   (Semi-Struct) │   │    (Spreadsheet)│  │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  设计原则: 统一接口 │ 插件化扩展 │ 资源自动管理 │ 错误标准化       │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 架构设计哲学

| 哲学维度 | 具体体现 | 设计依据 |
|----------|----------|----------|
| **统一抽象** | 定义 BaseConnector / BaseFileConnector 抽象基类 | 上层业务代码无需关心数据源差异 |
| **插件化** | 工厂函数 + 延迟导入动态加载 | 新增数据源无需修改核心代码 |
| **资源安全** | 上下文管理器自动管理连接生命周期 | 防止连接泄漏，确保资源释放 |
| **错误标准化** | 统一的 Result 数据结构 | 调用方统一处理成功/失败 |

### 1.3 与传统 ORM 的差异

| 维度 | 传统 ORM (SQLAlchemy) | Connectors 系统 |
|------|----------------------|-----------------|
| **定位** | ORM 映射 + 查询构建 | 轻量连接器 + 直接 SQL |
| **复杂度** | 功能丰富但重量级 | 聚焦核心功能，轻量级 |
| **学习曲线** | 需要学习 ORM 概念 | 简单 API，直接 SQL |
| **性能** | 有抽象开销 | 直接执行，无额外开销 |
| **适用场景** | 应用开发 | 数据分析/ETL/查询 |

---

## 2 设计原则与理念

### 2.1 标准化接口原则

所有连接器必须实现统一的抽象接口：

```python
# Data Warehouse 连接器接口
class BaseConnector(ABC):
    connector_name: str
    default_timeout: int
    
    def connect(): ...
    def disconnect(): ...
    def execute(sql, params) -> QueryResult: ...
    def export(sql, output_path, format): ...

# File Connector 接口
class BaseFileConnector(ABC):
    connector_name: str
    supported_formats: list
    
    def read(file_path, **kwargs) -> FileResult: ...
    def write(data, file_path, **kwargs) -> FileResult: ...
```

### 2.2 工厂模式原则

使用工厂函数统一创建连接器实例：

```python
# 统一的入口，隐藏具体实现细节
def create_connector(connector_type: str, config: dict):
    """返回 BaseConnector 实例"""
    
def create_tool_connector(connector_type: str, config: dict):
    """返回 BaseFileConnector 实例"""
```

### 2.3 资源管理原则

使用上下文管理器确保资源安全：

```python
# 自动连接建立和关闭
with create_connector('mysql', config) as conn:
    result = conn.execute("SELECT * FROM sales")
# 自动 disconnect() 被调用
```

### 2.4 配置优先原则

支持多种配置来源，优先级明确：

```
CLI 参数 > 环境变量 > 配置文件 > 默认值
```

### 2.5 结果标准化原则

所有连接器返回统一的结果数据结构：

```
QueryResult (Data Warehouse):
- columns: 列名列表
- rows: 行数据列表
- row_count: 行数
- execution_time_ms: 执行时间
- to_csv() / to_json() / to_dataframe() 转换方法

FileResult (File Connector):
- success: 是否成功
- output_path: 文件路径
- row_count: 行数
- columns: 列名列表
- error: 错误信息
```

---

## 3 设计方案

### 3.1 系统架构

```
connectors/
├── datawarehouse/              # 数据库连接器
│   ├── base.py                 # BaseConnector 抽象基类
│   ├── mysql.py                # MySQL 连接器
│   ├── clickhouse.py           # ClickHouse OLAP 连接器
│   ├── postgres.py             # PostgreSQL 连接器
│   ├── oracle.py               # Oracle 连接器
│   └── __init__.py             # 导出工厂函数
│
└── tool/                       # 文件类连接器
    ├── base.py                 # BaseFileConnector 抽象基类
    ├── csv_connector.py        # CSV/TSV 连接器
    ├── json_connector.py       # JSON/JSONL 连接器
    ├── excel_connector.py      # Excel 连接器
    ├── python_connector.py     # Python 脚本执行器
    └── __init__.py             # 导出工厂函数
```

### 3.2 数据模型设计

#### 3.2.1 QueryResult (数据库查询结果)

```python
@dataclass
class QueryResult:
    columns: List[str]           # 列名列表
    rows: List[List[Any]]        # 行数据 (嵌套列表)
    row_count: int               # 行数
    execution_time_ms: float     # 执行时间 (毫秒)
    format: str = "csv"          # 格式标记
    
    def to_csv(self, path):      # 导出 CSV
    def to_json(self, path):     # 导出 JSON
    def to_dataframe(self):      # 转换为 pandas DataFrame
```

#### 3.2.2 FileResult (文件操作结果)

```python
@dataclass
class FileResult:
    success: bool                # 是否成功
    output_path: Optional[str]   # 输出路径
    row_count: int = 0          # 行数
    columns: List[str] = []      # 列名列表
    error: Optional[str] = None # 错误信息
```

### 3.3 模板方法模式

```
BaseConnector (抽象基类)
    │
    ├── connect()               # 模板方法 - 公共逻辑
    │   └── _do_connect()       # 抽象方法 - 子类实现
    │
    ├── disconnect()            # 模板方法 - 公共逻辑
    │   └── _do_disconnect()    # 抽象方法 - 子类实现
    │
    ├── execute()               # 模板方法 - 公共逻辑
    │   └── _do_execute()       # 抽象方法 - 子类实现
    │
    └── export()                # 模板方法 - 公共逻辑
```

### 3.4 连接器能力矩阵

| 连接器 | 类型 | 读取 | 写入 | 执行 | 导出 | 超时 |
|--------|------|------|------|------|------|------|
| MySQL | RDBMS | ✓ | ✓ | ✓ | CSV/JSON | 120s |
| PostgreSQL | RDBMS | ✓ | ✓ | ✓ | CSV/JSON | 120s |
| Oracle | RDBMS | ✓ | ✓ | ✓ | CSV/JSON | 300s |
| ClickHouse | OLAP | ✓ | - | ✓ | CSV/JSON | 300s |
| CSV | File | ✓ | ✓ | - | - | - |
| JSON | File | ✓ | ✓ | - | - | - |
| Excel | File | ✓ | ✓ | - | - | - |
| Python | Script | ✓ | - | ✓ | - | 300s |

### 3.5 配置管理

#### 3.5.1 Data Warehouse 配置

```python
# 必需配置
config = {
    "host": "localhost",      # 主机
    "port": 3306,            # 端口
    "database": "dbname",    # 数据库名
    "user": "username",      # 用户名
    "password": "xxx",       # 密码
}

# 环境变量支持 (自动读取)
# MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE...
```

#### 3.5.2 File Connector 配置

```python
# CSV 配置
config = {
    "delimiter": ",",        # 分隔符
    "encoding": "utf-8",     # 编码
    "has_header": True,      # 有表头
}

# JSON 配置
config = {
    "encoding": "utf-8",
    "format": "array",       # array=数组, object=包装对象
}

# Excel 配置
config = {
    "sheet_name": "Sheet1",  # 工作表名
}
```

---

## 4 执行流程

### 4.1 连接器创建流程

```
┌──────────────────────────────────────────────────────────────────┐
│                  连接器创建流程                                    │
└──────────────────────────────────────────────────────────────────┘

1. 调用方请求创建连接器
   │
   ▼
2. create_connector(type, config)
   │
   ▼
3. 检查 connector_type 是否在映射表中
   │  ┌──────────────────────────────────┐
   │  │  connector_map = {               │
   │  │    'mysql': 'MySQLConnector',    │
   │  │    'clickhouse': 'ClickHouse...',│
   │  │    ...                           │
   │  │  }                               │
   │  └──────────────────────────────────┘
   │
   ├─ 类型不存在 ──→ ValueError
   │
   ▼
4. 延迟导入模块
   │  module = __import__(f'.{connector_type}')
   │
   ▼
5. 获取连接器类并实例化
   │  connector_class = getattr(module, class_name)
   │  return connector_class(config)
   │
   ▼
6. 执行 __init__
   │  ├─ 保存配置
   │  ├─ 调用 _validate_config() 验证必需配置
   │  └─ 环境变量回退
   │
   ▼
7. 返回连接器实例
```

### 4.2 数据库查询执行流程

```
┌──────────────────────────────────────────────────────────────────┐
│                数据库查询执行流程                                  │
└──────────────────────────────────────────────────────────────────┘

1. 调用 execute(sql, params)
   │
   ▼
2. 检查连接状态
   │  if _connection is None:
   │      connect()  →  _do_connect() → 建立连接
   │
   ▼
3. 记录日志
   │  logger.info(f"Executing: {sql[:100]}...")
   │
   ▼
4. 执行查询
   │  result = _do_execute(sql, params)
   │  │
   │  ├─ MySQL: pymysql.cursor.execute()
   │  ├─ ClickHouse: Client.execute()
   │  ├─ PostgreSQL: psycopg2.cursor.execute()
   │  └─ Oracle: oracledb.cursor.execute()
   │
   ▼
5. 性能监控
   │  execution_time_ms = (time.time() - start) * 1000
   │
   ▼
6. 返回 QueryResult
   │  - columns: 列名列表
   │  - rows: 行数据
   │  - row_count: 行数
   │  - execution_time_ms: 执行时间
   │
   ▼
7. 记录日志
   │  logger.info(f"Returned {row_count} rows")
```

### 4.3 文件读写执行流程

```
┌──────────────────────────────────────────────────────────────────┐
│                文件读写执行流程                                    │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐     ┌─────────────────────────┐
│      Read 流程          │     │      Write 流程         │
└───────────┬─────────────┘     └───────────┬─────────────┘
            │                               │
            ▼                               ▼
    读取文件路径                      接收数据列表
            │                               │
            ▼                               ▼
    解析参数选项                      解析参数选项
    (encoding, delimiter,            (encoding, format,
     has_header, max_rows)           indent, sheet_name)
            │                               │
            ▼                               ▼
    处理压缩格式                      确保目录存在
    (gzip, None)                     (_ensure_dir)
            │                               │
            ▼                               ▼
    读取数据                          构建输出数据
    (csv reader /                     (format 转换)
     json.load /                      ────────────
     pandas.read_excel)               array / object
            │                               │
            ▼                               ▼
    返回 FileResult                   写入文件
    - success: true                   (csv writer /
    - row_count: N                    json dump /
    - columns: [...]                  pandas to_excel)
            │                               │
            ▼                               ▼
            └───────→ 返回 FileResult ←──────┘
                          │
              ┌───────────┴───────────┐
              │                       │
          success=true            success=false
              │                       │
              ▼                       ▼
        返回结果对象            返回错误信息
```

### 4.4 连接生命周期管理

```
┌──────────────────────────────────────────────────────────────────┐
│                连接生命周期管理                                    │
└──────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────┐
    │           手动管理模式                       │
    └─────────────────────────────────────────────┘

    conn = create_connector('mysql', config)
    conn.connect()        # 手动建立连接
    │
    try:
        result = conn.execute(sql)
        # 处理结果
    finally:
        conn.disconnect() # 手动关闭连接


    ┌─────────────────────────────────────────────┐
    │           上下文管理器模式 (推荐)             │
    └─────────────────────────────────────────────┘

    with create_connector('mysql', config) as conn:
        result = conn.execute(sql)
        # 处理结果
    # 自动调用 disconnect()


    ┌─────────────────────────────────────────────┐
    │           每次执行模式 (简单查询)            │
    └─────────────────────────────────────────────┘

    conn = create_connector('mysql', config)
    result = conn.execute(sql)  # 自动 connect()
    # 内部维护连接池或长连接
```

---

## 5 模块协同

### 5.1 与 Skills 的协同

```
Skills 层调用 Connectors

┌─────────────────────────────────────────────────────────────┐
│                      Skills                                  │
├─────────────────────────────────────────────────────────────┤
│  data-query Skill                                            │
│       │                                                      │
│       ├─→ 读取配置 (数据源类型、连接信息)                     │
│       │                                                      │
│       ├─→ create_connector(source_type, config)             │
│       │                                                      │
│       ├─→ conn.execute(sql)                                 │
│       │        │                                             │
│       │        ├─→ MySQL/PostgreSQL/Oracle                  │
│       │        ├─→ ClickHouse (OLAP 专用)                  │
│       │        └─→ 文件: CSV/JSON/Excel                     │
│       │                                                      │
│       └─→ result.to_dataframe() / result.to_csv()          │
│                                                              │
│  data-clean Skill                                           │
│       │                                                      │
│       └─→ tool_connector.read() → 读取待清洗文件             │
│           tool_connector.write() → 写入清洗后文件            │
│                                                              │
│  visual Skill                                               │
│       │                                                      │
│       └─→ tool_connector.write() → 导出图表数据              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 与 Rules/Checks 的协同

```
┌─────────────────────────────────────────────────────────────┐
│               Rules/Checks 协同                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Rules: 连接器配置校验                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ access-control.md                                       │ │
│  │   ├─ 验证数据库连接是否有权限                           │ │
│  │   └─ 验证文件路径是否有访问权限                         │ │
│  │                                                          │ │
│  │ data-freshness.md                                       │ │
│  │   └─ 数据源是否支持实时/准实时查询                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Checks: 连接器执行结果校验                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ data-quality-check                                     │ │
│  │   ├─ 读取后: 空值/异常值/重复值检测                     │ │
│  │   └─ 输出前: 导出文件质量验证                           │ │
│  │                                                          │ │
│  │ caliber-consistency-check                              │ │
│  │   └─ 验证数据源指标口径是否一致                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 与 Industry Data 的协同

```
┌─────────────────────────────────────────────────────────────┐
│             Industry Data 系统协同                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Industry Data 存储 → Connectors 导出                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  store.py (IndustryStore)                             │  │
│  │   ├─ 加载 YAML 行业配置                                │  │
│  │   ├─ 同步到 SQLite                                     │  │
│  │   └─ 使用 file_connector 读写文件                      │  │
│  │         ├─→ CSVConnector (批量数据)                   │  │
│  │         └─→ JSONConnector (配置数据)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Industry Data 检索 → Data Warehouse 查询                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  retriever.py (IndustryRetriever)                     │  │
│  │   ├─ FTS5 全文搜索 (SQLite)                           │  │
│  │   ├─ N-gram 向量相似度                                │  │
│  │   └─ 使用 mysql/clickhouse 连接器查询                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 与 Learn 系统的协同

```
┌─────────────────────────────────────────────────────────────┐
│               Learn 学习系统协同                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  观察记录存储                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  learn/data/observations/                             │  │
│  │   └─ 使用 CSVConnector / JSONConnector 存储观察记录   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Instinct 应用                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  learn/scripts/instinct-engine.py                    │  │
│  │   └─ 使用 PythonConnector 执行分析脚本                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.5 全局协同架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        dAnalyzer 全局协同架构                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐                                                   │
│  │    CLI       │ ←── 用户入口                                      │
│  └──────┬───────┘                                                 │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────┐               │
│  │             danalyzer-core Agent                  │               │
│  │  ┌─────────────────────────────────────────┐      │               │
│  │  │  需求理解 → 技能决策 → 规则加载 → 执行   │      │               │
│  │  └─────────────────────────────────────────┘      │               │
│  └──────────────────────┬───────────────────────────┘               │
│                         │                                            │
│         ┌───────────────┼───────────────┐                           │
│         │               │               │                           │
│         ▼               ▼               ▼                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │   Skills   │ │   Rules    │ │   Checks   │                   │
│  │            │ │            │ │            │                   │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                   │
│         │               │               │                           │
│         └───────────────┼───────────────┘                           │
│                         │                                            │
│                         ▼                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Connectors 系统                           │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐          │   │
│  │  │   Data Warehouse   │  │       Tool          │          │   │
│  │  │   (数据库连接器)    │  │   (文件连接器)      │          │   │
│  │  │  ┌───────────────┐ │  │  ┌───────────────┐  │          │   │
│  │  │  │ MySQL        │ │  │  │ CSV          │  │          │   │
│  │  │  │ PostgreSQL   │ │  │  │ JSON         │  │          │   │
│  │  │  │ Oracle       │ │  │  │ Excel        │  │          │   │
│  │  │  │ ClickHouse  │ │  │  │ Python       │  │          │   │
│  │  │  └───────────────┘ │  │  └───────────────┘  │          │   │
│  │  └─────────────────────┘  └─────────────────────┘          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    数据资产 (knowledge/)                    │     │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │     │
│  │  │  industry/  │ │   model/    │ │  template/  │     │     │
│  │  └──────────────┘ └──────────────┘ └──────────────┘     │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6 优劣势分析

### 6.1 设计优势

#### 6.1.1 统一接口抽象

| 优势 | 说明 |
|------|------|
| **代码复用** | 公共逻辑在基类实现，子类只需关注差异 |
| **易于维护** | 修改公共逻辑只需改一处 |
| **类型安全** | 抽象基类定义明确接口契约 |
| ** IDE 支持** | 类型提示和自动补全 |

#### 6.1.2 插件化架构

| 优势 | 说明 |
|------|------|
| **零侵入** | 新增数据源无需修改核心代码 |
| **动态加载** | 延迟导入减少启动时间 |
| **按需加载** | 只导入实际使用的连接器 |
| **解耦** | 模块间无直接依赖 |

#### 6.1.3 资源安全管理

| 优势 | 说明 |
|------|------|
| **自动释放** | 上下文管理器自动关闭连接 |
| **异常安全** | finally 确保资源释放 |
| **防泄漏** | 减少连接泄漏风险 |

#### 6.1.4 结果标准化

| 优势 | 说明 |
|------|------|
| **统一处理** | 调用方统一处理 QueryResult/FileResult |
| **灵活转换** | 内置 to_csv/to_json/to_dataframe 方法 |
| **易于测试** | 标准化的 Mock 对象 |

### 6.2 设计挑战

#### 6.2.1 SQL 方言差异

| 挑战 | 描述 |
|------|------|
| **语法差异** | 不同数据库 SQL 语法有差异 |
| **函数差异** | 日期函数、字符串函数不同 |
| **分页语法** | LIMIT/OFFSET vs ROWNUM vs TOP |

**当前处理**:
- 基础 SQL 统一支持
- 特殊语法需要调用方适配
- 后续可考虑 SQL 转换层

#### 6.2.2 连接池管理

| 挑战 | 描述 |
|------|------|
| **性能** | 每次查询新建连接开销大 |
| **并发** | 多线程场景需要连接池 |
| **配置** | 连接池参数需要调优 |

**当前状态**:
- 基础版本: 每次执行自动重连
- 后续可集成 SQLAlchemy Pool 或连接池库

#### 6.2.3 错误处理一致性

| 挑战 | 描述 |
|------|------|
| **异常类型** | 不同驱动抛出不同异常 |
| **错误信息** | 错误消息格式不统一 |
| **重试机制** | 网络异常时需要重试 |

**当前处理**:
- 统一包装为 RuntimeError
- 包含原始错误信息

#### 6.2.4 大文件处理

| 挑战 | 描述 |
|------|------|
| **内存** | 大文件可能 OOM |
| **流式** | 不支持流式读写 |
| **分片** | 无分片上传/下载 |

**当前状态**:
- 基础版本适合小中型文件
- 大文件场景需扩展

### 6.3 与行业实践对比

| 维度 | 本设计 | SQLAlchemy | Pandas IO | 专业 ETL |
|------|--------|-------------|-----------|----------|
| **复杂度** | 轻量 | 中等 | 轻量 | 重 |
| **学习成本** | 低 | 高 | 低 | 高 |
| **性能** | 高 | 中 | 中 | 高 |
| **功能** | 基础 | 完整 | 基础 | 专业 |
| **数据源** | 4+4 | 多种 | 多种 | 多种 |
| **连接池** | 基础 | 支持 | - | 支持 |
| **类型安全** | 好 | 好 | 中 | 好 |

### 6.4 改进建议

| 优先级 | 建议 | 说明 |
|--------|------|------|
| **高** | 连接池支持 | 集成 SQLAlchemy Pool 或自定义池 |
| **高** | SQL 转换层 | 统一分页/日期函数等语法差异 |
| **中** | 异步支持 | asyncio 版本连接器 |
| **中** | 大文件流式处理 | 迭代器模式支持大文件 |
| **低** | 更多数据源 | Spark, BigQuery, Snowflake 等 |

---

## 7 总结

### 7.1 设计核心理念

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   Connectors 系统核心理念                                      │
│                                                                │
│   统一抽象 ─── 插件化扩展 ─── 资源安全 ─── 结果标准            │
│       │           │           │          │                    │
│       ▼           ▼           ▼          ▼                    │
│   BaseConnec   工厂函数    上下文管理   QueryResult          │
│   模板方法     延迟导入    自动释放     FileResult           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 7.2 价值总结

| 价值维度 | 具体体现 |
|----------|----------|
| **简化调用** | 统一的 API，无视数据源差异 |
| **快速集成** | 新数据源只需实现基类方法 |
| **安全可靠** | 上下文管理器防止资源泄漏 |
| **灵活输出** | 支持多种导出格式 |
| **易于测试** | 标准接口便于 Mock |
| **轻量高效** | 无 ORM 开销，直接 SQL |

### 7.3 文件统计

| 目录 | 文件 | 说明 |
|------|------|------|
| datawarehouse/ | base.py | 抽象基类 |
| datawarehouse/ | mysql.py | MySQL 连接器 |
| datawarehouse/ | clickhouse.py | ClickHouse 连接器 |
| datawarehouse/ | postgres.py | PostgreSQL 连接器 |
| datawarehouse/ | oracle.py | Oracle 连接器 |
| tool/ | base.py | 文件连接器基类 |
| tool/ | csv_connector.py | CSV 连接器 |
| tool/ | json_connector.py | JSON 连接器 |
| tool/ | excel_connector.py | Excel 连接器 |
| tool/ | python_connector.py | Python 脚本执行器 |
| **总计** | **10 个 Python 文件** | |

### 7.4 使用示例

```python
# 数据库查询示例
from connectors import create_connector

# 创建 MySQL 连接器
config = {"host": "localhost", "port": 3306, "database": "sales", "user": "root", "password": "xxx"}
with create_connector('mysql', config) as conn:
    result = conn.execute("SELECT * FROM orders WHERE date >= '2026-01-01'")
    print(f"查询到 {result.row_count} 条记录")
    df = result.to_dataframe()  # 转换为 DataFrame

# 文件读写示例
from connectors import create_tool_connector

# 读取 CSV
csv_conn = create_tool_connector('csv')
result = csv_conn.read('knowledge/sales.csv', delimiter=',', encoding='utf-8')

# 写入 JSON
json_conn = create_tool_connector('json')
result = json_conn.write(data, 'output/result.json', format='array', indent=2)
```

---

*本文档详细阐述了 dAnalyzer 系统中 Connectors 的设计哲学、原则、方案、执行流程、协同机制以及优劣势分析。*

*版本: 1.0*
*更新日期: 2026-04-26*
