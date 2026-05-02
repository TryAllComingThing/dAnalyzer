# 行业配置说明

> dAnalyzer 行业适配机制的核心目录

## 目录结构

```
data/industry/
├── _base/                  # 基础配置（所有行业共用）
│   ├── config.yaml         # 通用设置
│   └── common-indicator.md # 通用指标
│
├── ecommerce/              # 电商行业
│   └── config.yaml         # 电商配置
│
├── logistics/              # 物流行业
│   └── config.yaml         # 物流配置
│
├── manufacturing/          # 生产制造行业
│   └── config.yaml         # 制造配置
│
└── finance/                # 金融行业
    └── config.yaml         # 金融配置
```

## 行业配置内容

每个行业配置文件包含：

| 配置项 | 说明 |
|--------|------|
| `industry` | 行业基础信息（名称、代码、数据源） |
| `indicators` | 行业专属业务指标 |
| `mappings` | 表结构映射（NL2SQL 核心） |
| `analysis_templates` | 分析模板 |
| `insight_templates` | 洞察生成模板 |

## 使用方式

### 切换行业

```
用户: /set-industry logistics
用户: 查询今日配送数据
```

### 自动识别

```
用户: 查询今日订单量

danalyzer-core:
  → 检测"订单"关键词
  → 自动加载 ecommerce 配置
  → 执行查询
```

## 新增行业

如需新增行业，步骤：

1. 创建目录: `data/industry/{行业代码}/`
2. 创建配置文件: `config.yaml`
3. 配置行业指标、表映射、分析模板、洞察模板
4. 无需修改任何代码

## 行业列表

| 行业 | 代码 | 状态 |
|------|------|------|
| 电商 | ecommerce | ✅ 默认 |
| 物流 | logistics | ✅ 已配置 |
| 生产制造 | manufacturing | ✅ 已配置 |
| 金融 | finance | ✅ 已配置 |

## 与其他目录的关系

```
rules/           # 行业无关约束
data/model/      # 行业无关方法
data/template/   # 行业无关模板
data/industry/   # ⭐ 行业相关配置（可切换）
```

---

*本文档于 2026-04-25 更新*
