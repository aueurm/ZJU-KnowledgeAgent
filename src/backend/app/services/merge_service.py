"""
跨教材整合服务
职责：计算知识点相似度、生成整合决策
"""
import math
import os
from typing import List, Tuple
from app.models import MergeDecision


class MergeService:
    """整合服务"""

    def __init__(self):
        self.embedding_model = None
        try:
            from sentence_transformers import SentenceTransformer
            model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
            self.embedding_model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            # ponytail: 字符相似度兜底，装好 sentence-transformers 后自动切回向量相似度。
            self.embedding_model = None

        # 相似度阈值配置
        self.HIGH_THRESHOLD = float(os.getenv("MERGE_HIGH_THRESHOLD", "0.92"))
        self.MID_THRESHOLD = float(os.getenv("MERGE_MID_THRESHOLD", "0.80"))
        self.NAME_THRESHOLD = float(os.getenv("MERGE_NAME_THRESHOLD", "0.75"))
        self.LOW_THRESHOLD = 0.50     # 低置信度，保留各自版本

    def compute_similarity(self, node1: dict, node2: dict) -> float:
        """
        计算两个知识点的语义相似度
        输入：两个知识点节点
        返回：相似度分数（0-1）
        """
        # 将知识点名称和定义拼接
        text1 = f"{node1.get('name', '')} {node1.get('definition', '')}"
        text2 = f"{node2.get('name', '')} {node2.get('definition', '')}"

        name_similarity = self._simple_similarity(
            str(node1.get("name", "")),
            str(node2.get("name", ""))
        )

        if not self.embedding_model:
            text_similarity = self._simple_similarity(text1, text2)
            return max(text_similarity, name_similarity)

        emb1 = self.embedding_model.encode(text1)
        emb2 = self.embedding_model.encode(text2)
        return max(self._cosine(emb1, emb2), name_similarity)

    def _cosine(self, emb1, emb2) -> float:
        dot = sum(float(a) * float(b) for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(float(a) * float(a) for a in emb1))
        norm2 = math.sqrt(sum(float(b) * float(b) for b in emb2))
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

    def _simple_similarity(self, text1: str, text2: str) -> float:
        chars1 = {c for c in text1.lower() if not c.isspace()}
        chars2 = {c for c in text2.lower() if not c.isspace()}
        if not chars1 or not chars2:
            return 0.0
        return len(chars1 & chars2) / len(chars1 | chars2)

    def _can_auto_merge(self, node1: dict, node2: dict) -> bool:
        name1 = str(node1.get("name", "")).strip()
        name2 = str(node2.get("name", "")).strip()
        if not name1 or not name2:
            return False
        if name1 == name2:
            return True
        return self._simple_similarity(name1, name2) >= self.NAME_THRESHOLD

    def merge_graphs(self, graphs: List[dict]) -> Tuple[dict, List[MergeDecision]]:
        """
        合并多个教材图谱
        输入：多个图谱数据列表
        返回：(合并后图谱, 整合决策列表)
        """
        decisions = []
        all_nodes = []
        all_edges = []

        # 收集所有节点
        for graph in graphs:
            all_nodes.extend(graph.get("nodes", []))

        # 构建节点映射（新ID -> 合并后节点）
        node_mapping = {}

        # 计算相似度矩阵
        for i in range(len(all_nodes)):
            for j in range(i + 1, len(all_nodes)):
                similarity = self.compute_similarity(all_nodes[i], all_nodes[j])

                if (
                    similarity >= self.HIGH_THRESHOLD
                    and self._can_auto_merge(all_nodes[i], all_nodes[j])
                ):
                    # 高置信度，直接合并
                    decision = self._create_merge_decision(
                        [all_nodes[i], all_nodes[j]],
                        similarity
                    )
                    decisions.append(decision)

                    # 更新映射
                    merged_id = decision.result_node
                    node_mapping[all_nodes[i]["id"]] = merged_id
                    node_mapping[all_nodes[j]["id"]] = merged_id

                elif similarity >= self.MID_THRESHOLD:
                    # 中置信度先保留，交给用户确认是否改成 merge/remove
                    decisions.append(MergeDecision(
                        decision_id=f"merge_{len(decisions)+1:03d}",
                        action="keep",
                        affected_nodes=[all_nodes[i]["id"], all_nodes[j]["id"]],
                        reason="语义相似但未达到自动合并阈值，建议人工确认",
                        confidence=similarity
                    ))

        # 构建合并后的图谱
        merged_nodes = self._build_merged_nodes(all_nodes, node_mapping)
        merged_edges = self._build_merged_edges(
            [e for g in graphs for e in g.get("edges", [])],
            node_mapping
        )

        return {"nodes": merged_nodes, "edges": merged_edges}, decisions

    def _create_merge_decision(self, nodes: List[dict], confidence: float) -> MergeDecision:
        """创建合并决策"""
        # 选择描述最完整的节点作为主版本
        best_node = max(nodes, key=lambda n: len(n.get("definition", "")))

        return MergeDecision(
            decision_id=f"merge_{abs(hash(tuple(n['id'] for n in nodes))) % 100000:05d}",
            action="merge",
            affected_nodes=[n["id"] for n in nodes],
            result_node=f"merged_{best_node['id']}",
            reason=f"多个教材都讲解了'{best_node.get('name', best_node['id'])}'，保留描述更完整的版本",
            confidence=confidence
        )

    def _build_merged_nodes(self, all_nodes: List[dict], node_mapping: dict) -> List[dict]:
        """构建合并后的节点列表"""
        merged = []
        seen = set()

        for node in all_nodes:
            new_id = node_mapping.get(node["id"], node["id"])

            if new_id not in seen:
                merged.append({
                    **node,
                    "id": new_id,
                    "freq": 1
                })
                seen.add(new_id)
            else:
                # 累加频次
                for m in merged:
                    if m["id"] == new_id:
                        m["freq"] = m.get("freq", 1) + 1
                        incoming = str(node.get("definition", "")).strip()
                        current = str(m.get("definition", "")).strip()
                        if incoming and incoming not in current:
                            m["definition"] = f"{current}\n补充：{incoming}" if current else incoming
                        break

        return merged

    def _build_merged_edges(self, all_edges: List[dict], node_mapping: dict) -> List[dict]:
        """构建合并后的边列表"""
        merged = []
        seen_edges = set()

        for edge in all_edges:
            # 映射节点ID
            new_source = node_mapping.get(edge["source"], edge["source"])
            new_target = node_mapping.get(edge["target"], edge["target"])
            if new_source == new_target:
                continue

            edge_key = (new_source, new_target)
            if edge_key not in seen_edges:
                merged.append({
                    **edge,
                    "source": new_source,
                    "target": new_target
                })
                seen_edges.add(edge_key)

        return merged
