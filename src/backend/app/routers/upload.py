"""
教材上传路由
职责：处理教材文件上传、解析、存储
核心流程：上传 → 解析PDF → 提取知识 → 构建图谱 → 建立RAG索引
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
import tempfile
import os
import asyncio
import pathlib

from app.models import TextbookUploadResponse, Chapter
from app.services.logger import get_logger

# 导入共享存储（与graph.py共用）
from app.routers.graph import store_graph, get_rag_service

router = APIRouter()
logger = get_logger(__name__)

# 教材存储（与graph.py共用）
_textbooks: dict = {}


def update_textbook_status(textbook_id: str, **fields):
    """更新教材状态，后台任务和轮询接口共用。"""
    if textbook_id in _textbooks:
        _textbooks[textbook_id].update(fields)


@router.post("", response_model=TextbookUploadResponse)
@router.post("/", response_model=TextbookUploadResponse)
async def upload_textbook(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    上传教材文件
    接收：PDF/MD/TXT/DOCX文件
    返回：教材ID和解析状态
    """
    logger.info("收到上传请求，文件名: %s", file.filename)

    # 检查文件格式
    allowed_extensions = [".pdf", ".md", ".txt", ".docx"]
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        logger.error("不支持的文件格式: %s", file.filename)
        raise HTTPException(status_code=400, detail="不支持的文件格式")

    # 生成教材ID
    textbook_id = f"book_{len(_textbooks) + 1:03d}"

    # 保存到临时文件 - 使用项目本地目录避免中文路径问题
    temp_dir = pathlib.Path(__file__).parent.parent.parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    tmp_suffix = f".{filename.split('.')[-1]}"
    with tempfile.NamedTemporaryFile(dir=str(temp_dir), delete=False, suffix=tmp_suffix) as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        tmp_path = tmp.name

    # 初始化教材状态
    _textbooks[textbook_id] = {
        "textbook_id": textbook_id,
        "filename": file.filename,
        "title": file.filename.rsplit(".", 1)[0],
        "total_pages": 0,
        "total_chars": 0,
        "status": "parsing",
        "progress": 0,
        "current_step": "已接收文件，等待解析",
        "error": None,
        "warning": None,
        "chapters": []
    }

    # 启动后台处理管道
    if background_tasks:
        background_tasks.add_task(process_textbook_pipeline, textbook_id, tmp_path)

    logger.info("教材上传成功，ID: %s，文件名: %s", textbook_id, file.filename)
    return TextbookUploadResponse(
        textbook_id=textbook_id,
        filename=file.filename,
        status="parsing",
        message="上传成功，正在后台解析..."
    )


async def process_textbook_pipeline(textbook_id: str, file_path: str):
    """
    教材处理管道：解析→提取知识→存储图谱→建立RAG索引
    """
    logger.info("开始后台处理管道，教材ID: %s", textbook_id)
    try:
        # Step 1: 解析文件
        update_textbook_status(textbook_id, progress=5, current_step="正在解析文件")
        from app.services.parser_service import get_parser_service
        parser = get_parser_service(file_path)
        loop = asyncio.get_event_loop()
        parsed_data = await loop.run_in_executor(None, parser.parse, file_path)
        logger.info(
            "教材解析完成，教材ID: %s | 页数: %d | 章节数: %d",
            textbook_id, parsed_data["total_pages"], len(parsed_data["chapters"])
        )

        # 更新状态
        chapters = parsed_data["chapters"]
        if not chapters:
            raise ValueError("PDF 未提取到可解析文本，请确认文件不是扫描版图片 PDF")

        update_textbook_status(
            textbook_id,
            total_pages=parsed_data["total_pages"],
            progress=20,
            current_step=f"文件解析完成，共 {len(chapters)} 个内容片段"
        )

        # Step 2: 知识提取
        from app.services.extractor_service import KnowledgeExtractorService
        from app.services.llm_client import get_llm_client
        llm_client = get_llm_client()
        extractor = KnowledgeExtractorService(llm_client)

        normalized_chapters = [
            Chapter(
                chapter_id=chapter_data.chapter_id,
                title=chapter_data.title,
                page_start=chapter_data.page_start,
                page_end=chapter_data.page_end,
                content=chapter_data.content,
                char_count=chapter_data.char_count
            )
            for chapter_data in chapters
        ]
        total_chars = sum(chapter.char_count for chapter in normalized_chapters)
        concurrency = max(1, int(os.getenv("EXTRACT_CONCURRENCY", "3")))
        semaphore = asyncio.Semaphore(concurrency)
        completed = 0

        async def extract_one(index: int, chapter: Chapter):
            nonlocal completed
            async with semaphore:
                update_textbook_status(
                    textbook_id,
                    progress=20 + int(65 * completed / len(normalized_chapters)),
                    current_step=f"正在提取知识 {completed}/{len(normalized_chapters)}（并发 {concurrency}）：{chapter.title}"
                )
                result = await loop.run_in_executor(
                    None,
                    extractor.extract,
                    chapter.content,
                    chapter.title,
                    textbook_id
                )
                completed += 1
                update_textbook_status(
                    textbook_id,
                    progress=20 + int(65 * completed / len(normalized_chapters)),
                    current_step=f"已提取知识 {completed}/{len(normalized_chapters)}：{chapter.title}"
                )
                return index, chapter, result

        results = await asyncio.gather(*[
            extract_one(index, chapter)
            for index, chapter in enumerate(normalized_chapters, start=1)
        ])

        all_nodes = []
        all_edges = []
        for _, chapter, result in sorted(results, key=lambda item: item[0]):
            node_ids = {}
            for node in result.get("nodes", []):
                old_id = node.get("id") or f"n{len(node_ids) + 1}"
                node["id"] = f"{textbook_id}_{chapter.chapter_id}_{old_id}"
                node_ids[old_id] = node["id"]
                node.setdefault("name", old_id)
                node.setdefault("definition", "")
                node.setdefault("category", "知识点")
                node["source"] = textbook_id
                node["chapter"] = chapter.title
                node.setdefault("page", max(1, chapter.page_start))
                all_nodes.append(node)

            for edge in result.get("edges", []):
                if not edge.get("source") or not edge.get("target"):
                    continue
                edge["source"] = node_ids.get(edge["source"], edge["source"])
                edge["target"] = node_ids.get(edge["target"], edge["target"])
                all_edges.append(edge)

        if not all_nodes:
            raise ValueError("知识提取未返回节点，请检查 LLM_API_BASE、LLM_MODEL 和 API Key 是否可用")

        # 更新字数统计
        update_textbook_status(
            textbook_id,
            total_chars=total_chars,
            progress=88,
            current_step="正在保存图谱",
            chapters=[
            {
                "chapter_id": c.chapter_id,
                "title": c.title,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "content": c.content,
                "char_count": c.char_count
            }
            for c in normalized_chapters
            ]
        )

        # Step 3: 存储图谱
        from app.models import GraphData
        graph_data = GraphData(nodes=all_nodes, edges=all_edges)
        store_graph(textbook_id, graph_data)

        # Step 4: 构建RAG索引
        update_textbook_status(textbook_id, progress=92, current_step="正在建立 RAG 索引")
        warning = None
        try:
            rag_service = get_rag_service()
            chunks = create_chunks(normalized_chapters, textbook_id)
            await loop.run_in_executor(None, rag_service.build_index, textbook_id, chunks)
        except Exception as e:
            warning = f"RAG 索引失败：{e}"
            logger.error("RAG索引失败，ID: %s | 错误: %s", textbook_id, str(e), exc_info=True)

        # Step 5: 更新状态为完成
        update_textbook_status(
            textbook_id,
            status="parsed",
            progress=100,
            current_step="解析完成",
            warning=warning
        )
        logger.info("教材处理完成，ID: %s | 总字数: %d", textbook_id, total_chars)

    except Exception as e:
        update_textbook_status(
            textbook_id,
            status="failed",
            progress=100,
            current_step="处理失败",
            error=str(e)
        )
        logger.error("教材处理失败，ID: %s | 错误: %s", textbook_id, str(e), exc_info=True)

    finally:
        # 删除临时文件
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info("临时文件已删除: %s", file_path)


def create_chunks(chapters: List, textbook_id: str) -> List[dict]:
    """
    将章节内容分块，用于RAG索引
    """
    chunks = []
    chunk_size = 600
    overlap = 80

    for chapter in chapters:
        content = chapter.content if hasattr(chapter, 'content') else chapter.get('content', '')
        if not content or len(content.strip()) < 50:
            continue

        paragraphs = content.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    "chunk_id": f"{textbook_id}_{chapter.chapter_id}_{len(chunks)}",
                    "content": current_chunk,
                    "textbook": textbook_id,
                    "chapter": chapter.title,
                    "page": chapter.page_start
                })
                overlap_start = max(0, len(current_chunk) - overlap)
                current_chunk = current_chunk[overlap_start:] + "\n\n" + para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk and len(current_chunk.strip()) > 50:
            chunks.append({
                "chunk_id": f"{textbook_id}_{chapter.chapter_id}_{len(chunks)}",
                "content": current_chunk,
                "textbook": textbook_id,
                "chapter": chapter.title,
                "page": chapter.page_start
            })

    return chunks


@router.get("/list")
async def get_textbook_list():
    """
    获取已上传教材列表
    """
    return {"textbooks": list(_textbooks.values())}


@router.get("/{textbook_id}")
async def get_textbook_detail(textbook_id: str):
    """
    获取单本教材详情
    """
    if textbook_id not in _textbooks:
        raise HTTPException(status_code=404, detail="教材不存在")
    return _textbooks[textbook_id]


@router.get("/status/{textbook_id}")
async def get_textbook_status(textbook_id: str):
    """
    获取教材处理状态
    """
    if textbook_id not in _textbooks:
        raise HTTPException(status_code=404, detail="教材不存在")
    textbook = _textbooks[textbook_id]
    return {
        "textbook_id": textbook_id,
        "status": textbook["status"],
        "progress": textbook.get("progress", 0),
        "current_step": textbook.get("current_step", ""),
        "total_pages": textbook.get("total_pages", 0),
        "total_chars": textbook.get("total_chars", 0),
        "error": textbook.get("error", None),
        "warning": textbook.get("warning", None)
    }
