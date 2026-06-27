"""
RAG精准问答路由
职责：建立索引、问答查询、状态查询
集成RAGService实现真正的RAG功能
"""
from fastapi import APIRouter, HTTPException
from app.models import RAGQuery, RAGResponse, RAGStatus, Citation
from app.routers.graph import get_rag_service

router = APIRouter()


@router.post("/index")
async def build_rag_index(textbook_id: str = None):
    """
    为已上传教材建立向量索引
    如果指定 textbook_id：只为该教材建立索引
    否则：为所有已解析的教材重建索引
    """
    rag_service = get_rag_service()

    if textbook_id:
        # 为指定教材构建索引
        from app.routers.upload import _textbooks
        if textbook_id not in _textbooks:
            raise HTTPException(status_code=404, detail="教材不存在")

        textbook = _textbooks[textbook_id]
        if textbook.get("status") != "parsed":
            raise HTTPException(status_code=400, detail=f"教材状态为 {textbook.get('status')}，需先解析完成")

        # 重建该教材的索引
        from app.routers.upload import create_chunks
        chunks = create_chunks(textbook.get("chapters", []), textbook_id)
        rag_service.build_index(textbook_id, chunks)
    else:
        # 重建所有教材的索引
        from app.routers.upload import _textbooks
        for tid, textbook in _textbooks.items():
            if textbook.get("status") == "parsed":
                from app.routers.upload import create_chunks
                chunks = create_chunks(textbook.get("chapters", []), tid)
                rag_service.build_index(tid, chunks)

    status = rag_service.get_status()
    return RAGStatus(**status)


@router.post("/query")
async def rag_query(query: RAGQuery):
    """
    RAG精准问答
    输入：用户问题
    返回：回答和引用来源
    """
    rag_service = get_rag_service()
    result = await rag_service.query(query.question)

    return RAGResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
        source_chunks=result["source_chunks"]
    )


@router.get("/status")
async def get_rag_status():
    """
    查询RAG索引状态
    返回：已索引教材数、知识块总数
    """
    rag_service = get_rag_service()
    status = rag_service.get_status()
    return RAGStatus(**status)