"""
RAG问答服务
职责：构建向量索引、检索相关chunk、生成回答
"""
from typing import List

from app.services.llm_client import get_llm_client


class RAGService:
    """RAG服务"""

    def __init__(self, persist_dir: str = "./data/embeddings"):
        self.collection = None
        self.embedding_model = None
        self.memory_chunks = []

        try:
            import os
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer

            self.chroma_client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name="textbook_chunks",
                metadata={"hnsw:space": "cosine"}
            )
            model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
            self.embedding_model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            # ponytail: 无 Chroma/BGE 时用内存检索兜底，演示可跑；生产装 requirements 后自动用向量库。
            self.collection = None
            self.embedding_model = None

    def build_index(self, textbook_id: str, chunks: List[dict]):
        """
        为教材构建向量索引
        输入：教材ID、知识块列表
        """
        if not self.collection:
            self.memory_chunks = [
                item for item in self.memory_chunks
                if item.get("textbook") != textbook_id
            ]
            self.memory_chunks.extend(chunks)
            return

        old = self.collection.get(where={"textbook": textbook_id})
        if old.get("ids"):
            self.collection.delete(ids=old["ids"])

        embeddings = []
        documents = []
        metadatas = []
        ids = []
        for chunk in chunks:
            # 生成向量
            embedding = self.embedding_model.encode(chunk["content"])

            embeddings.append(embedding.tolist())
            documents.append(chunk["content"])
            metadatas.append({
                "textbook": chunk.get("textbook", textbook_id),
                "chapter": chunk.get("chapter", ""),
                "page": chunk.get("page", 0)
            })
            ids.append(f"{textbook_id}_{chunk['chunk_id']}")

        if ids:
            self.collection.upsert(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    def retrieve(self, question: str, top_k: int = 5) -> List[dict]:
        """
        检索相关chunks
        输入：问题、返回数量
        返回：相关chunks列表
        """
        if not self.collection:
            return self._memory_retrieve(question, top_k)

        # 问题转向量
        question_embedding = self.embedding_model.encode(question)

        # 向量检索
        results = self.collection.query(
            query_embeddings=[question_embedding.tolist()],
            n_results=top_k
        )

        # 整理返回结果
        chunks = []
        for i in range(len(results["ids"][0])):
            chunks.append({
                "content": results["documents"][0][i],
                "textbook": results["metadatas"][0][i]["textbook"],
                "chapter": results["metadatas"][0][i]["chapter"],
                "page": results["metadatas"][0][i]["page"],
                "relevance_score": float(results["distances"][0][i])
            })

        return chunks

    def _memory_retrieve(self, question: str, top_k: int) -> List[dict]:
        q_chars = {c for c in question.lower() if not c.isspace()}
        scored = []
        for chunk in self.memory_chunks:
            content = chunk.get("content", "")
            c_chars = {c for c in content.lower() if not c.isspace()}
            score = len(q_chars & c_chars) / len(q_chars | c_chars) if q_chars and c_chars else 0
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "content": chunk.get("content", ""),
                "textbook": chunk.get("textbook", ""),
                "chapter": chunk.get("chapter", ""),
                "page": chunk.get("page", 0),
                "relevance_score": score
            }
            for score, chunk in scored[:top_k]
        ]

    async def query(self, question: str) -> dict:
        """
        RAG问答
        输入：用户问题
        返回：回答和引用来源
        """
        # 1. 检索相关chunks
        chunks = self.retrieve(question, top_k=5)

        if not chunks:
            return {
                "answer": "当前知识库中未找到相关信息",
                "citations": [],
                "source_chunks": []
            }

        # 2. 构建上下文
        context = "\n\n".join([
            f"【来源：{c['textbook']}, {c['chapter']}, 第{c['page']}页】\n{c['content']}"
            for c in chunks
        ])

        # 3. 构建Prompt
        prompt = f"""你是一个学科知识助手，只能基于提供的教材内容回答问题。

【教材内容】
{context}

【问题】
{question}

【回答要求】
1. 只基于上述教材内容回答，不使用自身知识
2. 每个回答必须附带来源引用，格式：[教材名, 章节, 页码]
3. 如果上下文中找不到答案，回复"当前知识库中未找到相关信息"

请回答："""

        # 4. 调用LLM生成回答
        llm = get_llm_client()
        answer = await llm.call(prompt, temperature=0.3)

        # 5. 构建引用列表
        citations = [{
            "textbook": c["textbook"],
            "chapter": c["chapter"],
            "page": c["page"],
            "relevance_score": c["relevance_score"]
        } for c in chunks]

        return {
            "answer": answer,
            "citations": citations,
            "source_chunks": [c["content"] for c in chunks]
        }

    def get_status(self) -> dict:
        """获取索引状态"""
        if not self.collection:
            textbooks = {
                chunk.get("textbook", "")
                for chunk in self.memory_chunks
                if chunk.get("textbook")
            }
            return {
                "indexed_textbooks": len(textbooks),
                "total_chunks": len(self.memory_chunks),
                "status": "ready"
            }

        data = self.collection.get(include=["metadatas"])
        return {
            "indexed_textbooks": len(set(
                item.get("textbook", "") for item in data.get("metadatas", []) if item.get("textbook")
            )),
            "total_chunks": self.collection.count(),
            "status": "ready"
        }
