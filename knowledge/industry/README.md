# 行业配置说明

> dAnalyzer 行业适配机制 — 快消 (FMCG) 领域

## 目录结构

```
knowledge/industry/
└── fmcg/                   # 快消行业
    ├── config.yaml         # 行业配置
    ├── preferences.yaml    # 默认偏好
    ├── indicators/         # 指标字典 (38个)
    │   ├── sales_amount.yaml       # 销售额
    │   ├── sales_volume.yaml       # 销售量
    │   ├── gross_profit.yaml       # 毛利额
    │   ├── gross_margin_rate.yaml  # 毛利率
    │   ├── net_profit.yaml         # 净利润额
    │   ├── net_margin_rate.yaml    # 净利率
    │   ├── discount_rate.yaml      # 折扣率
    │   ├── avg_order_value.yaml    # 客单价
    │   ├── avg_basket_size.yaml    # 连带率
    │   ├── order_count.yaml        # 订单量
    │   ├── order_id.yaml           # 订单ID
    │   ├── order_cancel_rate.yaml  # 订单取消率
    │   ├── return_rate.yaml        # 退货率
    │   ├── delivery_on_time_rate.yaml # 准时交付率
    │   ├── sku_count.yaml          # SKU数量
    │   ├── sell_through_rate.yaml  # 动销率
    │   ├── new_sku_ratio.yaml      # 新品占比
    │   ├── out_of_stock_rate.yaml  # 缺货率
    │   ├── inventory_turnover.yaml # 库存周转率
    │   ├── inventory_days.yaml     # 库存周转天数
    │   ├── product_defect_rate.yaml # 产品不良率
    │   ├── user_id.yaml            # 用户ID
    │   ├── new_user_count.yaml     # 新增用户数
    │   ├── active_user_count.yaml  # 活跃用户数
    │   ├── user_retention_rate.yaml # 用户留存率
    │   ├── repurchase_rate.yaml    # 复购率
    │   ├── member_count.yaml       # 会员数
    │   ├── clv.yaml                # 客户终身价值
    │   ├── conversion_rate.yaml    # 转化率
    │   ├── visit_count.yaml        # 访问量
    │   ├── promotion_roi.yaml      # 促销ROI
    │   ├── coupon_usage_rate.yaml  # 优惠券使用率
    │   ├── customer_acquisition_cost.yaml # 获客成本
    │   ├── channel_revenue_share.yaml     # 渠道收入占比
    │   ├── terminal_coverage_rate.yaml    # 终端覆盖率
    │   ├── distribution_penetration.yaml  # 铺货率
    │   ├── distributor_count.yaml  # 经销商数量
    │   └── status.yaml             # 状态
    ├── scenarios/          # 分析场景 (12个)
    │   ├── sales_trend.yaml            # 销售趋势
    │   ├── category_analysis.yaml      # 品类分析
    │   ├── channel_analysis.yaml       # 渠道分析
    │   ├── user_analysis.yaml          # 用户分析
    │   ├── promotion_analysis.yaml     # 促销效果
    │   ├── inventory_analysis.yaml     # 库存分析
    │   ├── profit_analysis.yaml        # 利润分析
    │   ├── customer_value_analysis.yaml # 客户价值
    │   ├── return_analysis.yaml        # 退货分析
    │   ├── regional_analysis.yaml      # 区域分析
    │   ├── new_product_analysis.yaml   # 新品分析
    │   └── market_basket_analysis.yaml # 购物篮分析
    └── mappings/           # 字段映射
        └── common_mapping.yaml
```

## 指标分类总览

| 分类 | 数量 | 涵盖领域 |
|------|------|---------|
| 销售与收入 | 9 | 销售额/量、毛利、净利、折扣、客单价、连带率 |
| 订单与服务 | 5 | 订单量/ID、取消率、退货率、准时交付 |
| 商品与库存 | 7 | SKU、动销、新品、缺货、周转、不良率 |
| 用户与客户 | 7 | 新增/活跃/留存/复购、会员、CLV |
| 流量与营销 | 5 | 转化率、访问量、促销ROI、券使用率、获客成本 |
| 渠道与分销 | 4 | 渠道占比、终端覆盖、铺货率、经销商 |
| 其他 | 1 | 状态 |

## 动态发现

`scripts/registry_scanner.py` 自动扫描 `knowledge/industry/` 下所有非隐藏目录。
新增行业只需创建目录 + YAML 文件，无需修改代码。

## 版本

- v4.0 - 2026-05-01 — 快消行业大幅扩充（38指标 + 12场景）
