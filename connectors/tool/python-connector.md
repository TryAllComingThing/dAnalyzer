---
name: python-connector
description: Python脚本对接配置，支持执行Python脚本、数据处理和机器学习模型
type: tool
capabilities:
  - script_execution
  - data_processing
  - ml_model_execution
  - custom_algorithm
origin: ECC
---

# Python脚本对接配置

## 工具信息

- 名称：Python
- 版本：3.8+
- 类型：脚本工具

## 支持操作

- 执行Python脚本
- 数据处理脚本
- 机器学习模型
- 自定义算法

## 接口规范

### 脚本执行

```bash
python script.py --input data.csv --output result.csv
```

### 数据交互

- 输入：CSV/JSON文件
- 输出：CSV/JSON文件
- 参数：命令行参数

## 常用库支持

- 数据处理：pandas, numpy
- 数据分析：scipy, statsmodels
- 机器学习：sklearn, xgboost
- 可视化：matplotlib, seaborn

## 错误处理

- 脚本错误：记录日志
- 超时：终止进程
- 内存溢出：预警

## 输出格式

- 统一输出为CSV格式
- 保持原始格式（如图表）
