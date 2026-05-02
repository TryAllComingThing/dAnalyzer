# 企业级数分静态资产库 (data)

## 目录用途

企业级数分静态资产库，统一归档可复用的标准化资产。主要包括：

- **指标资产（indicator）**：指标字典、口径定义、统计规则
- **模板资产（template）**：SQL模板、报表模板、可视化模板
- **模型资产（model）**：行业分析模型、归因框架
- **样本资产（sample）**：标准样本库、异常样本库

> 注：从ecc-data的assets重命名为data，以符合Plugin规范

## 目录结构

```
data/
├── indicator/       # 指标资产 (8个)
│   ├── core-indicator-dict.md
│   ├── custom-indicator.md
│   ├── finance-indicator.md
│   ├── marketing-indicator.md
│   ├── operation-indicator.md
│   ├── product-indicator.md
│   ├── sales-indicator.md
│   └── user-indicator.md
├── model/            # 模型资产 (9个)
│   ├── aarrr-model.md
│   ├── attribution-model.md
│   ├── cohort-model.md
│   ├── funnel-model.md
│   ├── prediction-model.md
│   ├── rfm-model.md
│   ├── scoring-model.md
│   ├── segmentation-model.md
│   └── correlation-analysis.md
├── template/         # 模板资产 (6个)
│   ├── common-sql-template.md
│   ├── export-template.md
│   ├── funnel-sql-template.md
│   ├── report-template.md
│   ├── time-analysis-template.md
│   └── user-analysis-template.md
└── sample/          # 样本资产 (5个)
    ├── standard-data-sample.md
    ├── abnormal-data-sample.md
    ├── report-sample.md
    ├── sql-example-sample.md
    └── test-case-sample.md
```

## 资产列表 (28个)

### indicator (指标资产) - 8个
| 资产 | 说明 |
|------|------|
| core-indicator-dict | 核心指标字典 |
| custom-indicator | 自定义指标 |
| finance-indicator | 财务指标 |
| marketing-indicator | 营销指标 |
| operation-indicator | 运营指标 |
| product-indicator | 产品指标 |
| sales-indicator | 销售指标 |
| user-indicator | 用户指标 |

### model (模型资产) - 9个
| 资产 | 说明 |
|------|------|
| aarrr-model | AARRR模型 |
| attribution-model | 归因模型 |
| cohort-model | 同期群模型 |
| funnel-model | 漏斗模型 |
| prediction-model | 预测模型 |
| rfm-model | RFM模型 |
| scoring-model | 评分模型 |
| segmentation-model | 用户分群模型 |
| correlation-analysis | 相关性分析 |

### template (模板资产) - 6个
| 资产 | 说明 |
|------|------|
| common-sql-template | 通用SQL模板 |
| export-template | 导出模板 |
| funnel-sql-template | 漏斗SQL模板 |
| report-template | 报告模板 |
| time-analysis-template | 时间分析模板 |
| user-analysis-template | 用户分析模板 |

### sample (样本资产) - 5个
| 资产 | 说明 |
|------|------|
| standard-data-sample | 标准数据样本 |
| abnormal-data-sample | 异常数据样本 |
| report-sample | 报告样本 |
| sql-example-sample | SQL示例样本 |
| test-case-sample | 测试用例样本 |

## 调用规范

### 路径格式
```
data/[资产类型]/[文件名].md
```

### 调用要求
1. 技能、流程调用资产时，确保**资产口径、格式统一**
2. 资产变更需遵循**版本管理规范**
3. 资产可被Agent、调度器、流程、CLI快捷指令调用

## 资产版本管理

1. 资产更新需标注版本号（如v1.0、v1.1）
2. 旧版本通过 git 历史管理，不单独维护 version 副本
3. CLI优先调用最新版本资产
4. 回滚时记录回滚日志

## 文件统计

- indicator: 8个
- model: 9个
- template: 6个
- sample: 5个
- **总计: 28个md文件**

## 注意事项

1. 资产口径必须与指标字典保持一致
2. 模板资产支持参数替换
3. 样本数据需脱敏处理
4. 资产变更需通知相关方
