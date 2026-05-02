# 领域知识资产库 (knowledge)

## 目录用途

企业级数分领域知识资产库，统一归档可复用的标准化资产。

## 目录结构

```
knowledge/
├── industry/              # 行业配置
│   └── fmcg/              # 快消行业 (FMCG)
│       ├── config.yaml        # 行业配置
│       ├── preferences.yaml   # 用户偏好
│       ├── indicators/        # 指标字典 (38个)
│       ├── scenarios/         # 分析场景 (12个)
│       └── mappings/          # 字段映射
├── model/                 # 分析模型 (5个)
│   ├── aarrr-model.md
│   ├── cohort-model.md
│   ├── prediction-model.md
│   ├── scoring-model.md
│   └── segmentation-model.md
├── template/              # 模板资产 (6个)
│   ├── common-sql-template.md
│   ├── export-template.md
│   ├── funnel-sql-template.md
│   ├── report-template.md
│   ├── time-analysis-template.md
│   └── user-analysis-template.md
└── intent-routing.yaml    # 意图路由映射
```

## 快消行业 (FMCG)

### 指标分类 (38个)

| 分类 | 指标 | code | 说明 |
|------|------|------|------|
| 销售与收入 | 销售额 | sales_amount | 核心收入指标 |
| | 销售量 | sales_volume | 销售件数 |
| | 毛利额 | gross_profit | 直接盈利 |
| | 毛利率 | gross_margin_rate | 盈利水平 |
| | 净利润额 | net_profit | 最终利润 |
| | 净利率 | net_margin_rate | 净利占比 |
| | 折扣率 | discount_rate | 折让占比 |
| | 客单价 | avg_order_value | 笔均金额 |
| | 连带率 | avg_basket_size | 笔均件数 |
| 订单与服务 | 订单量 | order_count | 核心交易量 |
| | 订单ID | order_id | 交易标识 |
| | 订单取消率 | order_cancel_rate | 取消比例 |
| | 退货率 | return_rate | 退货比例 |
| | 准时交付率 | delivery_on_time_rate | 配送时效 |
| 商品与库存 | SKU数量 | sku_count | 品类宽度 |
| | 动销率 | sell_through_rate | 有销SKU占比 |
| | 新品占比 | new_sku_ratio | 新品贡献 |
| | 缺货率 | out_of_stock_rate | 库存不足 |
| | 库存周转率 | inventory_turnover | 库存效率 |
| | 库存周转天数 | inventory_days | 库存消化 |
| | 产品不良率 | product_defect_rate | 品控水平 |
| 用户与客户 | 用户ID | user_id | 消费者标识 |
| | 新增用户数 | new_user_count | 拉新能力 |
| | 活跃用户数 | active_user_count | 用户活跃度 |
| | 用户留存率 | user_retention_rate | 用户粘性 |
| | 复购率 | repurchase_rate | 品牌忠诚 |
| | 会员数 | member_count | 会员规模 |
| | 客户终身价值 | clv | 客户总贡献 |
| 流量与营销 | 转化率 | conversion_rate | 访客到下单 |
| | 访问量 | visit_count | 流量规模 |
| | 促销ROI | promotion_roi | 促销回报 |
| | 优惠券使用率 | coupon_usage_rate | 券核销率 |
| | 获客成本 | customer_acquisition_cost | 拉新费用 |
| 渠道与分销 | 渠道收入占比 | channel_revenue_share | 各渠道贡献 |
| | 终端覆盖率 | terminal_coverage_rate | 网点覆盖 |
| | 铺货率 | distribution_penetration | 上架覆盖 |
| | 经销商数量 | distributor_count | 渠道规模 |
| 其他 | 状态 | status | 订单/商品状态 |

### 分析场景 (12个)

| 场景 | code | 说明 |
|------|------|------|
| 销售趋势 | sales_trend | 时间维度销售分析 |
| 品类分析 | category_analysis | 品类结构/排名/动销 |
| 渠道分析 | channel_analysis | 渠道效能/占比 |
| 用户分析 | user_analysis | 消费者画像/复购 |
| 促销效果 | promotion_analysis | 活动ROI/券核销 |
| 库存分析 | inventory_analysis | 周转/缺货/滞销 |
| 利润分析 | profit_analysis | 毛利/净利/亏损 |
| 客户价值 | customer_value_analysis | 分层/CLV/留存 |
| 退货分析 | return_analysis | 退货率/原因/损失 |
| 区域分析 | regional_analysis | 区域销售/覆盖 |
| 新品分析 | new_product_analysis | 新品贡献/存活 |
| 购物篮分析 | market_basket_analysis | 关联购买/连带 |

## 调用规范

- 数据读取通过 Connector 统一接口，禁止直接 find/grep knowledge/
- 行业上下文检索通过 `python scripts/retrieve_context.py`
- 动态注册表通过 `python scripts/registry_scanner.py`

## 版本

- v4.0 - 2026-05-01 — 快消行业大幅扩充（38指标 + 12场景）
