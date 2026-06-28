"""
知识提取服务
职责：调用LLM从章节内容中提取知识点和关系
"""
import json
import os
from typing import List, Dict
from app.models import KnowledgeNode, KnowledgeEdge


class KnowledgeExtractorService:
    """知识提取服务"""

    # 知识点提取Prompt模板
    EXTRACT_PROMPT = """
从以下教材内容中提取知识点，不要做摘要。

【章节内容】
{chapter_content}

【提取要求】
1. 提取核心概念、定理、方法、现象等知识点
2. 本批目标提取约 {target_nodes} 个知识点；内容很少时可少一些，但不要只提取几个总括词
3. 每个【片段】都要覆盖，优先提取原文反复出现、被定义、被举例或参与关系的术语
4. 每个知识点包含：name（名称）、definition（定义）、category（类型）、module（大模块）、page（最相关页码，整数）
5. 识别知识点间的关系（前置依赖/并列/包含/应用）
6. 如果【片段】标注了页码范围，page 必须取该范围内最相关的一页

【关系类型说明】
- prerequisite: 前置依赖（学习B需先掌握A）
- parallel: 并列关系（同一层级的平行概念）
- contains: 包含关系（上位概念包含下位概念）
- applies_to: 应用关系（某知识点是另一个的应用场景）

【输出格式】
严格输出JSON，格式如下：
{{
  "nodes": [
    {{"id": "n1", "name": "...", "definition": "...", "category": "...", "module": "下肢", "page": 12}}
  ],
  "edges": [
    {{"source": "n1", "target": "n2", "relation_type": "...", "description": "..."}}
  ]
}}
"""

    def __init__(self, llm_client):
        """初始化，注入LLM客户端"""
        self.llm = llm_client

    def extract(self, chapter_content: str, chapter_title: str, textbook_id: str) -> Dict:
        """
        从章节内容中提取知识点
        输入：章节内容、章节标题、教材ID
        返回：节点和边列表
        """
        # 构建Prompt
        target_nodes = min(80, max(12, len(chapter_content) // 1200))
        prompt = self.EXTRACT_PROMPT.format(
            chapter_content=chapter_content,
            target_nodes=target_nodes
        )

        # 调用LLM（同步调用）
        response = self.llm.call_sync(
            prompt,
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=int(os.getenv("LLM_EXTRACT_MAX_TOKENS", "12000"))
        )
        if response.startswith("LLM调用失败"):
            raise RuntimeError(response)

        # 解析JSON响应
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试提取其中的JSON部分
            result = self._extract_json_from_response(response)

        # 添加教材来源到节点
        for node in result.get("nodes", []):
            node["source"] = textbook_id
            node["chapter"] = chapter_title

        return result

    def _extract_json_from_response(self, response: str) -> Dict:
        """从响应中提取JSON（处理LLM输出格式问题）"""
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(response[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {"nodes": [], "edges": []}


def extract_knowledge(llm_client, chapter_content: str, chapter_title: str, textbook_id: str) -> Dict:
    """便捷函数：提取知识点"""
    extractor = KnowledgeExtractorService(llm_client)
    return extractor.extract(chapter_content, chapter_title, textbook_id)
