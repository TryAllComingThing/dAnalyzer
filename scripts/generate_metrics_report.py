"""
度量报表生成器

从 MetricsCollector SQLite 数据库读取数据，
生成 ECharts HTML 看板。

用法:
    python scripts/generate_metrics_report.py
    python scripts/generate_metrics_report.py --days 30 --output output/dashboard.html
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from metrics.collector import MetricsCollector


def build_timing_chart(daily_stats: list) -> str:
    """生成响应时间趋势图 (折线图)"""
    dates = [d["date"] for d in daily_stats]
    avg_ms = [d["avg_response_ms"] for d in daily_stats]
    runs = [d["runs"] for d in daily_stats]

    return json.dumps({
        "title": {"text": "管道响应时间趋势", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["平均响应时间(ms)", "运行次数"], "top": 30},
        "xAxis": {"type": "category", "data": dates, "axisLabel": {"rotate": 45}},
        "yAxis": [
            {"type": "value", "name": "响应时间 (ms)"},
            {"type": "value", "name": "运行次数"},
        ],
        "series": [
            {
                "name": "平均响应时间(ms)",
                "type": "line",
                "data": avg_ms,
                "smooth": True,
                "lineStyle": {"width": 3},
                "itemStyle": {"color": "#5470C6"},
            },
            {
                "name": "运行次数",
                "type": "bar",
                "yAxisIndex": 1,
                "data": runs,
                "itemStyle": {"color": "#91CC75"},
            },
        ],
        "grid": {"bottom": 80},
    }, ensure_ascii=False)


def build_industry_chart(stats: dict) -> str:
    """生成行业分布图 (饼图)"""
    data = [{"name": p["pipeline"], "value": p["count"]}
            for p in stats.get("by_pipeline", [])]

    return json.dumps({
        "title": {"text": "行业请求分布", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "series": [{
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["50%", "55%"],
            "data": data,
            "label": {"formatter": "{b}\n{c} 次"},
        }],
    }, ensure_ascii=False)


def build_security_chart(stats: dict) -> str:
    """生成安全事件图"""
    levels = stats.get("by_level", [])
    data = [{"name": l["level"], "value": l["count"]} for l in levels]

    return json.dumps({
        "title": {"text": "安全级别分布", "left": "center"},
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "pie",
            "data": data or [{"name": "LOW", "value": 1}],
            "label": {"formatter": "{b}: {c}"},
        }],
        "color": ["#91CC75", "#FAC858", "#EE6666", "#FF8C00"],
    }, ensure_ascii=False)


def build_timing_breakdown_chart(stats: dict) -> str:
    """生成步骤耗时分布图 (堆叠柱状图)"""
    timing = stats.get("avg_timing_ms", {})
    categories = ["retrieval", "loading", "analysis", "security"]
    labels = ["上下文检索", "数据加载", "数据分析", "安全扫描"]
    values = [timing.get(f"{c}_ms", timing.get(c, 0)) for c in categories]
    colors = ["#5470C6", "#91CC75", "#FAC858", "#EE6666"]

    return json.dumps({
        "title": {"text": "平均步骤耗时", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": ["各步骤平均耗时"]},
        "yAxis": {"type": "value", "name": "毫秒 (ms)"},
        "series": [
            {
                "name": label,
                "type": "bar",
                "stack": "total",
                "data": [value],
                "itemStyle": {"color": color},
            }
            for label, value, color in zip(labels, values, colors)
        ],
    }, ensure_ascii=False)


def build_daily_security_chart(daily_stats: list) -> str:
    """生成每日安全事件趋势图"""
    dates = [d["date"] for d in daily_stats]
    blocked = [d["blocked"] for d in daily_stats]
    masked = [d["masked"] for d in daily_stats]

    return json.dumps({
        "title": {"text": "每日安全事件", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["拦截次数", "脱敏次数"], "top": 30},
        "xAxis": {"type": "category", "data": dates, "axisLabel": {"rotate": 45}},
        "yAxis": {"type": "value", "name": "次数"},
        "series": [
            {
                "name": "拦截次数",
                "type": "bar",
                "data": blocked,
                "itemStyle": {"color": "#EE6666"},
            },
            {
                "name": "脱敏次数",
                "type": "line",
                "data": masked,
                "smooth": True,
                "itemStyle": {"color": "#FAC858"},
            },
        ],
        "grid": {"bottom": 80},
    }, ensure_ascii=False)


def generate_dashboard(collector: MetricsCollector, days: int = 30) -> str:
    """
    生成完整 HTML 看板

    Args:
        collector: MetricsCollector 实例 (必须已有数据)
        days: 统计天数

    Returns:
        完整 HTML 字符串
    """
    stats = collector.get_stats(
        since=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    )
    daily = collector.get_daily_stats(days)
    recent = collector.get_recent_runs(limit=10)

    timing_chart = build_timing_chart(daily)
    industry_chart = build_industry_chart(stats)
    security_chart = build_security_chart(stats)
    breakdown_chart = build_timing_breakdown_chart(stats)
    daily_security_chart = build_daily_security_chart(daily)

    # KPI 数据
    avg_timing = stats.get("avg_timing_ms", {})
    kpis = {
        "total_runs": stats.get("total_runs", 0),
        "avg_total_ms": avg_timing.get("total", 0),
        "success_rate": round(
            stats["successful_runs"] / stats["total_runs"] * 100, 1
        ) if stats.get("total_runs") else 0,
        "total_blocked": stats.get("security", {}).get("total_blocked", 0),
        "total_masked": stats.get("security", {}).get("total_masked", 0),
        "pipelines": len(stats.get("by_pipeline", [])),
    }

    # 最近运行表格行
    recent_rows = ""
    for r in recent:
        ts = r.get("timestamp", "")[:19]
        recent_rows += f"""
            <tr>
                <td>{ts}</td>
                <td>{r.get('pipeline', '')}</td>
                <td>{r.get('query', '')[:30]}</td>
                <td>{r.get('total_ms', 0):.0f}ms</td>
                <td>{r.get('security_level', '')}</td>
                <td>{'通过' if r.get('security_pass') else '拦截'}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>dAnalyzer 管道运行看板</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #f0f2f5; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 24px 32px; }}
        .header h1 {{ font-size: 24px; }}
        .header p {{ opacity: 0.9; margin-top: 4px; font-size: 14px; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 16px; margin-bottom: 20px; }}
        .kpi-card {{ background: white; border-radius: 12px; padding: 20px;
                     box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .kpi-card .label {{ font-size: 13px; color: #666; }}
        .kpi-card .value {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
        .kpi-card .value.green {{ color: #52c41a; }}
        .kpi-card .value.blue {{ color: #1890ff; }}
        .kpi-card .value.red {{ color: #ff4d4f; }}
        .kpi-card .value.orange {{ color: #fa8c16; }}
        .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
        .chart-card {{ background: white; border-radius: 12px; padding: 16px;
                       box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .chart-card.full {{ grid-column: 1 / -1; }}
        .chart {{ width: 100%; height: 360px; }}
        .table-wrap {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ background: #fafafa; padding: 10px 12px; text-align: left;
              font-weight: 600; border-bottom: 2px solid #f0f0f0; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }}
        tr:hover {{ background: #fafafa; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px;
                  font-size: 12px; font-weight: 500; }}
        .badge.LOW {{ background: #f6ffed; color: #52c41a; }}
        .badge.HIGH {{ background: #fff7e6; color: #fa8c16; }}
        .badge.CRITICAL {{ background: #fff2f0; color: #ff4d4f; }}
        @media (max-width: 768px) {{ .chart-row {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>dAnalyzer 管道运行看板</h1>
        <p>统计周期: 最近 {days} 天 · 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    <div class="container">
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="label">总运行次数</div>
                <div class="value blue">{kpis['total_runs']}</div>
            </div>
            <div class="kpi-card">
                <div class="label">平均响应时间</div>
                <div class="value blue">{kpis['avg_total_ms']} ms</div>
            </div>
            <div class="kpi-card">
                <div class="label">成功率</div>
                <div class="value green">{kpis['success_rate']}%</div>
            </div>
            <div class="kpi-card">
                <div class="label">安全拦截</div>
                <div class="value red">{kpis['total_blocked']}</div>
            </div>
            <div class="kpi-card">
                <div class="label">数据脱敏</div>
                <div class="value orange">{kpis['total_masked']}</div>
            </div>
            <div class="kpi-card">
                <div class="label">活跃管道数</div>
                <div class="value blue">{kpis['pipelines']}</div>
            </div>
        </div>

        <div class="chart-row">
            <div class="chart-card full">
                <div id="timingChart" class="chart"></div>
            </div>
        </div>
        <div class="chart-row">
            <div class="chart-card">
                <div id="industryChart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div id="securityChart" class="chart"></div>
            </div>
        </div>
        <div class="chart-row">
            <div class="chart-card">
                <div id="breakdownChart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div id="dailySecurityChart" class="chart"></div>
            </div>
        </div>

        <div class="chart-card full">
            <h3 style="margin-bottom:12px;">最近运行记录</h3>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>行业</th>
                            <th>查询</th>
                            <th>耗时</th>
                            <th>安全级别</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        {recent_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        function initChart(id, option) {{
            var chart = echarts.init(document.getElementById(id));
            chart.setOption(option);
            window.addEventListener('resize', function() {{ chart.resize(); }});
        }}
        initChart('timingChart', {timing_chart});
        initChart('industryChart', {industry_chart});
        initChart('securityChart', {security_chart});
        initChart('breakdownChart', {breakdown_chart});
        initChart('dailySecurityChart', {daily_security_chart});
    </script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 度量看板生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--days", "-d", type=int, default=30,
                        help="统计天数 (默认 30)")
    parser.add_argument("--output", "-o",
                        default="output/metrics_dashboard.html",
                        help="输出 HTML 文件路径")
    parser.add_argument("--db", help="Metrics SQLite 数据库路径 (默认自动)")

    args = parser.parse_args()

    collector = MetricsCollector(db_path=args.db) if args.db else MetricsCollector()

    print(f"[Dashboard] Generating report for last {args.days} days...", file=sys.stderr)

    html = generate_dashboard(collector, days=args.days)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"[Dashboard] Report written to {args.output}", file=sys.stderr)
    print(f"[Dashboard] Open in browser to view", file=sys.stderr)


if __name__ == "__main__":
    main()
