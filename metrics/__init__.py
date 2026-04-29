"""
dAnalyzer 度量收集模块

提供 SQLite 持久化度量收集器 MetricsCollector，
记录管道执行时间、检索准确率、安全拦截次数等。
"""

from metrics.collector import MetricsCollector

__all__ = ["MetricsCollector"]
