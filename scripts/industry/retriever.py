"""
dAnalyzer 行业数据检索模块

高级检索功能:
- FTS5 全文搜索
- N-gram 向量检索
- RRF 融合
- 时间衰减
- MMR 多样性重排
"""

import math
import hashlib
import re
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime


class IndustryRetriever:
    """
    行业数据检索器 (V2)

    特性:
    - FTS5 全文搜索 (SQLite 内置)
    - N-gram 向量检索 (纯 Python)
    - RRF 融合 (业界标准)
    - 时间衰减
    - MMR 多样性重排
    """

    def __init__(self, store):
        """
        初始化检索器

        Args:
            store: IndustryStore 实例
        """
        self.store = store
        self.db_path = store.db_path

        # 初始化 FTS5
        self._ensure_fts()

    # ==================== FTS5 初始化 ====================

    def _ensure_fts(self):
        """确保 FTS5 虚拟表存在"""
        conn = sqlite3.connect(str(self.db_path))

        try:
            # 检查是否需要重建 (简单检查)
            try:
                conn.execute("SELECT COUNT(*) FROM indicators_fts").fetchone()
                return  # 已存在
            except:
                pass

            # 删除旧的 FTS 表 (如果存在)
            try:
                conn.execute("DROP TABLE IF EXISTS indicators_fts")
                conn.execute("DROP TABLE IF EXISTS scenarios_fts")
            except:
                pass

            # 创建独立的 FTS5 表 (不使用 content 模式，避免触发器问题)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS indicators_fts USING fts5(
                    code,
                    name,
                    keywords,
                    description
                )
            """)

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS scenarios_fts USING fts5(
                    code,
                    name,
                    keywords,
                    description
                )
            """)

            conn.commit()

            # 填充数据
            self._populate_fts(conn)

        except sqlite3.Error as e:
            print(f"[IndustryRetriever] FTS5 init warning: {e}")
        finally:
            conn.close()

    def _populate_fts(self, conn: sqlite3.Connection):
        """填充 FTS5 数据"""
        try:
            # 填充指标
            indicators = conn.execute("SELECT code, name, keywords, description FROM indicators").fetchall()
            for ind in indicators:
                keywords = ind[2] or ""
                if isinstance(keywords, str):
                    pass  # 保持字符串
                conn.execute("""
                    INSERT INTO indicators_fts (code, name, keywords, description)
                    VALUES (?, ?, ?, ?)
                """, (ind[0], ind[1], keywords, ind[3] or ""))

            # 填充场景
            scenarios = conn.execute("SELECT code, name, keywords, description FROM scenarios").fetchall()
            for scn in scenarios:
                keywords = scn[2] or ""
                conn.execute("""
                    INSERT INTO scenarios_fts (code, name, keywords, description)
                    VALUES (?, ?, ?, ?)
                """, (scn[0], scn[1], keywords, scn[3] or ""))

            conn.commit()
        except sqlite3.Error as e:
            print(f"[IndustryRetriever] FTS5 populate error: {e}")

    def rebuild_fts(self):
        """重建 FTS5 索引"""
        conn = sqlite3.connect(str(self.db_path))

        try:
            # 清空并重建
            conn.execute("DELETE FROM indicators_fts")
            conn.execute("DELETE FROM scenarios_fts")

            self._populate_fts(conn)

            print("[IndustryRetriever] FTS5 rebuilt")
        except sqlite3.Error as e:
            print(f"[IndustryRetriever] FTS5 rebuild error: {e}")
        finally:
            conn.close()

    # ==================== FTS5 检索 ====================

    def fts_search(self, query: str, table: str = "indicators", top_k: int = 5) -> List[Dict]:
        """
        FTS5 全文搜索

        Args:
            query: 查询字符串 (支持 AND/OR/NOT)
            table: 表名 (indicators/scenarios)
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        if not query:
            return []

        conn = sqlite3.connect(str(self.db_path))
        columns = [desc[0] for desc in conn.execute(f"SELECT * FROM {table} LIMIT 1").description]

        # 预处理查询 (添加通配符支持中文)
        fts_query = self._prepare_fts_query(query)

        try:
            if table == "indicators":
                results = conn.execute("""
                    SELECT indicators.* FROM indicators
                    JOIN indicators_fts ON indicators.rowid = indicators_fts.rowid
                    WHERE indicators_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (fts_query, top_k)).fetchall()
            else:
                results = conn.execute("""
                    SELECT scenarios.* FROM scenarios
                    JOIN scenarios_fts ON scenarios.rowid = scenarios_fts.rowid
                    WHERE scenarios_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (fts_query, top_k)).fetchall()

            return [self._row_to_dict(row, columns) for row in results]

        except sqlite3.OperationalError as e:
            # FTS5 查询失败，回退到 LIKE
            print(f"[IndustryRetriever] FTS5 fallback: {e}")
            return self._like_search(query, table, top_k)

        finally:
            conn.close()

    def _prepare_fts_query(self, query: str) -> str:
        """预处理 FTS5 查询"""
        # 分词
        tokens = re.findall(r"[\w一-鿿]+", query.lower())

        if not tokens:
            return query

        # 构建 FTS5 查询
        # 使用 OR 连接，支持部分匹配
        fts_parts = []
        for token in tokens:
            if len(token) > 1:
                fts_parts.append(f'"{token}"*')
            else:
                fts_parts.append(token)

        return " OR ".join(fts_parts)

    # ==================== LIKE 回退 ====================

    def _like_search(self, query: str, table: str, top_k: int) -> List[Dict]:
        """LIKE 搜索 (FTS5 失败时的回退)"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [desc[0] for desc in conn.execute(f"SELECT * FROM {table} LIMIT 1").description]

        results = conn.execute(f"""
            SELECT * FROM {table}
            WHERE keywords LIKE ? OR name LIKE ? OR description LIKE ?
            ORDER BY importance DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", top_k)).fetchall()

        conn.close()
        return [self._row_to_dict(row, columns) for row in results]

    # ==================== N-gram 向量检索 ====================

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if not text:
            return []
        return [t for t in re.findall(r"[\w一-鿿]+", text.lower()) if len(t) > 1]

    def _ngram_hash_vector(self, text: str, dim: int = 128) -> List[float]:
        """
        N-gram 哈希向量

        使用字符级 3-gram + MD5 哈希，跨版本稳定
        """
        text = text.lower()
        ngrams = [text[i:i+3] for i in range(max(0, len(text)-2))]

        if not ngrams:
            return [0.0] * dim

        vec = [0.0] * dim
        for ngram in ngrams:
            # 使用 MD5 哈希 (稳定)
            h = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
            for i in range(min(dim // 16, 8)):
                vec[i * 16 + (h >> (i * 4)) % 16] += 1.0

        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def _get_text_for_vector(self, item: Dict) -> str:
        """获取用于向量化的文本"""
        parts = [
            item.get("name", ""),
            item.get("keywords", ""),
            item.get("description", "")
        ]
        # keywords 可能是列表
        if isinstance(item.get("keywords"), list):
            parts[1] = " ".join(item["keywords"])
        return " ".join(p for p in parts if p)

    def vector_search(self, query: str, table: str = "indicators", top_k: int = 5, dim: int = 128) -> List[Dict]:
        """
        N-gram 向量检索

        Args:
            query: 查询文本
            table: 表名
            top_k: 返回数量
            dim: 向量维度

        Returns:
            按相似度排序的结果
        """
        if not query:
            return []

        # 获取查询向量
        q_vec = self._ngram_hash_vector(query, dim)

        # 获取所有数据
        items = []
        if table == "indicators":
            items = self.store.get_all_indicators()
        else:
            items = self.store.get_all_scenarios()

        if not items:
            return []

        # 计算向量相似度
        results = []
        for item in items:
            text = self._get_text_for_vector(item)
            c_vec = self._ngram_hash_vector(text, dim)

            # 余弦相似度
            score = sum(q * c for q, c in zip(q_vec, c_vec))

            if score > 0:
                results.append({
                    "data": item,
                    "score": score
                })

        # 排序并返回
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # ==================== RRF 融合 ====================

    def rrf_fusion(self, results_lists: List[List[Dict]], k: int = 60) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 融合

        业界标准融合算法:
        score(doc) = Σ 1 / (k + rank(doc))

        Args:
            results_lists: 多个排序结果列表
            k: 融合参数 (通常 60)

        Returns:
            融合后的排序结果
        """
        scores = defaultdict(lambda: {"score": 0.0, "data": None})

        for results in results_lists:
            for rank, r in enumerate(results):
                doc_id = r.get("data", {}).get("code", r.get("data", {}).get("id", ""))
                scores[doc_id]["score"] += 1.0 / (k + rank + 1)
                scores[doc_id]["data"] = r.get("data", r)

        fused = [
            {"data": v["data"], "score": v["score"]}
            for v in scores.values()
        ]
        return sorted(fused, key=lambda x: x["score"], reverse=True)

    # ==================== 重排 ====================

    def temporal_decay(self, results: List[Dict], half_life_days: int = 30) -> List[Dict]:
        """
        时间衰减

        越新的数据权重越高
        """
        for r in results:
            updated = r.get("data", {}).get("updated", "")
            if updated:
                try:
                    dt = datetime.strptime(updated, "%Y-%m-%d")
                    days_ago = (datetime.now() - dt).days
                    decay = math.exp(-0.693 * days_ago / half_life_days)
                    r["score"] = r.get("score", 1.0) * decay
                except ValueError:
                    pass

        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    def mmr_rerank(self, results: List[Dict], lambda_param: float = 0.7) -> List[Dict]:
        """
        MMR 多样性重排

        平衡相关性和多样性
        """
        if len(results) <= 1:
            return results

        # 提取特征向量
        tokenized = []
        for r in results:
            text = self._get_text_for_vector(r.get("data", {}))
            tokenized.append(set(self._tokenize(text)))

        selected = []
        remaining = list(range(len(results)))
        reranked = []

        while remaining:
            best_idx = -1
            best_mmr = float("-inf")

            for idx in remaining:
                relevance = results[idx].get("score", 0)

                # 与已选结果的最大相似度
                max_sim = 0
                if selected:
                    similarities = []
                    for s in selected:
                        s_tokens = tokenized[s]
                        c_tokens = tokenized[idx]
                        if s_tokens and c_tokens:
                            sim = len(s_tokens & c_tokens) / len(s_tokens | c_tokens)
                            similarities.append(sim)
                    max_sim = max(similarities) if similarities else 0

                mmr = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = idx

            selected.append(best_idx)
            remaining.remove(best_idx)
            reranked.append(results[best_idx])

        return reranked

    # ==================== 统一检索接口 ====================

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_fts: bool = True,
        use_vector: bool = True,
        use_rrf: bool = True,
        use_temporal: bool = True,
        use_mmr: bool = False
    ) -> Dict[str, List[Dict]]:
        """
        统一检索接口 (高级版)

        Args:
            query: 查询关键词
            top_k: 返回数量
            use_fts: 使用 FTS5 全文搜索
            use_vector: 使用向量检索
            use_rrf: 使用 RRF 融合
            use_temporal: 使用时间衰减
            use_mmr: 使用 MMR 重排

        Returns:
            {
                "indicators": [...],
                "scenarios": [...],
                "query": query,
                "method": "fts+vector+rrf"  # 使用的检索方法
            }
        """
        methods = []

        # FTS5 检索
        fts_indicators = []
        fts_scenarios = []
        if use_fts:
            methods.append("fts")
            fts_indicators = [{"data": r, "score": 1.0 / (i + 1)} for i, r in enumerate(
                self.fts_search(query, "indicators", top_k)
            )]
            fts_scenarios = [{"data": r, "score": 1.0 / (i + 1)} for i, r in enumerate(
                self.fts_search(query, "scenarios", 3)
            )]

        # 向量检索
        vec_indicators = []
        vec_scenarios = []
        if use_vector:
            methods.append("vector")
            vec_indicators = self.vector_search(query, "indicators", top_k)
            vec_scenarios = self.vector_search(query, "scenarios", 3)

        # RRF 融合
        if use_rrf and (fts_indicators or vec_indicators):
            methods.append("rrf")
            ind_results = self.rrf_fusion([fts_indicators, vec_indicators])
            scn_results = self.rrf_fusion([fts_scenarios, vec_scenarios])
        else:
            ind_results = fts_indicators or vec_indicators
            scn_results = fts_scenarios or vec_scenarios

        # 时间衰减
        if use_temporal:
            methods.append("temporal")
            ind_results = self.temporal_decay(ind_results)
            scn_results = self.temporal_decay(scn_results)

        # MMR 重排
        if use_mmr:
            methods.append("mmr")
            ind_results = self.mmr_rerank(ind_results)
            scn_results = self.mmr_rerank(scn_results)

        return {
            "indicators": [r["data"] for r in ind_results[:top_k]],
            "scenarios": [r["data"] for r in scn_results[:3]],
            "query": query,
            "method": "+".join(methods) if methods else "basic",
            "scores": {
                "indicators": [(r["data"].get("code"), r.get("score", 0)) for r in ind_results[:top_k]],
                "scenarios": [(r["data"].get("code"), r.get("score", 0)) for r in scn_results[:3]]
            }
        }

    # ==================== 工具 ====================

    def _row_to_dict(self, row: Tuple, columns: Tuple) -> Dict:
        """行转字典"""
        if not row:
            return {}

        result = dict(zip(columns, row))

        # 解析 JSON 字段
        json_fields = ["keywords", "relations", "required_indicators",
                       "optional_indicators", "dimensions", "template"]
        for key in json_fields:
            if key in result and result[key]:
                try:
                    result[key] = json.loads(result[key])
                except (json.JSONDecodeError, TypeError):
                    pass

        return result

    def benchmark(self, queries: List[str]) -> Dict:
        """性能基准测试"""
        import time

        results = {
            "queries": [],
            "total_time": 0,
            "avg_time": 0
        }

        for query in queries:
            start = time.time()
            self.search(query)
            elapsed = time.time() - start

            results["queries"].append({
                "query": query,
                "time": elapsed * 1000  # ms
            })
            results["total_time"] += elapsed

        results["avg_time"] = (results["total_time"] / len(queries)) * 1000
        return results

    def __repr__(self):
        return f"IndustryRetriever(store={self.store})"


# ==================== 便捷函数 ====================

def get_retriever(store) -> IndustryRetriever:
    """获取检索器实例"""
    return IndustryRetriever(store)


# ==================== 测试 ====================

if __name__ == "__main__":
    from store import IndustryStore

    print("=" * 60)
    print("IndustryRetriever 测试")
    print("=" * 60)

    # 初始化
    store = IndustryStore("ecommerce")
    retriever = IndustryRetriever(store)

    # 测试 FTS5
    print("\n1. FTS5 检索 '销售':")
    fts_results = retriever.fts_search("销售", "indicators")
    for r in fts_results:
        print(f"   - {r.get('name')} ({r.get('code')})")

    # 测试向量检索
    print("\n2. 向量检索 '销售趋势':")
    vec_results = retriever.vector_search("销售趋势", "indicators")
    for r in vec_results[:3]:
        print(f"   - {r['data'].get('name')} (score: {r['score']:.3f})")

    # 测试高级检索
    print("\n3. 高级检索 (FTS + 向量 + RRF):")
    results = retriever.search("销售趋势", use_fts=True, use_vector=True, use_rrf=True)
    print(f"   方法: {results['method']}")
    print(f"   指标: {[r.get('name') for r in results['indicators']]}")
    print(f"   场景: {[r.get('name') for r in results['scenarios']]}")

    # 测试评分
    print("\n4. 评分详情:")
    print(f"   indicators: {results['scores']['indicators']}")
    print(f"   scenarios: {results['scores']['scenarios']}")

    # 基准测试
    print("\n5. 性能基准测试:")
    benchmark = retriever.benchmark(["销售", "订单", "转化", "趋势", "用户"])
    print(f"   平均延迟: {benchmark['avg_time']:.2f} ms")
    for q in benchmark["queries"]:
        print(f"   - {q['query']}: {q['time']:.2f} ms")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
