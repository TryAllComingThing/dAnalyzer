# -*- coding: utf-8 -*-
"""
pytest 配置文件
dAnalyzer 测试框架
"""

import pytest
import os
import sys
import csv
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 测试数据路径
TEST_DATA_DIR = Path(__file__).parent / "data" / "sample"


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def mysql_config():
    """MySQL 测试配置"""
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "database": os.getenv("MYSQL_DATABASE", "test"),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    }


@pytest.fixture
def sample_orders():
    """样本订单数据 (小规模)"""
    return [
        {
            "order_id": "O2024000001",
            "user_id": "U100001",
            "user_name": "用户00001",
            "product_id": "P10001",
            "category": "食品饮料",
            "brand": "农夫山泉",
            "quantity": 2,
            "unit_price": 50.0,
            "total_amount": 100.0,
            "discount_amount": 10.0,
            "actual_amount": 90.0,
            "payment_method": "支付宝",
            "order_status": "已支付",
            "order_date": "2024-01-01 10:00:00",
            "channel": "APP",
            "area": "华东",
            "city": "上海",
        },
        {
            "order_id": "O2024000002",
            "user_id": "U100002",
            "user_name": "用户00002",
            "product_id": "P10002",
            "category": "美妆护肤",
            "brand": "雅诗兰黛",
            "quantity": 1,
            "unit_price": 500.0,
            "total_amount": 500.0,
            "discount_amount": 50.0,
            "actual_amount": 450.0,
            "payment_method": "微信支付",
            "order_status": "已完成",
            "order_date": "2024-01-02 11:00:00",
            "channel": "小程序",
            "area": "华南",
            "city": "广州",
        },
    ]


@pytest.fixture
def sample_users():
    """样本用户数据"""
    return [
        {
            "user_id": "U100001",
            "user_name": "用户00001",
            "gender": "男",
            "age": 28,
            "area": "华东",
            "city": "上海",
            "phone": "13800138001",
            "email": "user1@example.com",
            "vip_level": "铂金",
            "points": 5000,
            "total_consume": 10000.0,
            "order_count": 50,
            "status": "正常",
        },
        {
            "user_id": "U100002",
            "user_name": "用户00002",
            "gender": "女",
            "age": 32,
            "area": "华南",
            "city": "广州",
            "phone": "13800138002",
            "email": "user2@example.com",
            "vip_level": "金卡",
            "points": 3000,
            "total_consume": 8000.0,
            "order_count": 30,
            "status": "正常",
        },
    ]


@pytest.fixture
def abnormal_orders():
    """异常订单数据"""
    return [
        # 极端值
        {"order_id": "O999999", "user_id": "U999", "actual_amount": 9999999.0},
        # 负数
        {"order_id": "O999998", "user_id": "U999", "actual_amount": -100.0},
        # 空值
        {"order_id": "O999997", "user_id": None, "actual_amount": 100.0},
        # 零值
        {"order_id": "O999996", "user_id": "U999", "quantity": 0},
    ]


def load_csv_data(filename: str) -> list:
    """加载 CSV 测试数据"""
    file_path = TEST_DATA_DIR / filename
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


@pytest.fixture
def orders_csv_data():
    """加载订单 CSV 数据"""
    return load_csv_data("test_orders.csv")


@pytest.fixture
def users_csv_data():
    """加载用户 CSV 数据"""
    return load_csv_data("test_users.csv")


@pytest.fixture
def products_csv_data():
    """加载商品 CSV 数据"""
    return load_csv_data("test_products.csv")


@pytest.fixture
def abnormal_csv_data():
    """加载异常数据 CSV"""
    return load_csv_data("test_abnormal.csv")
