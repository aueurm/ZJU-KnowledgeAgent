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
import json
import pathlib
import re

from app.models import TextbookUploadResponse, Chapter
from app.services.logger import get_logger

# 导入共享存储（与graph.py共用）
from app.routers.graph import store_graph, get_rag_service

router = APIRouter()
logger = get_logger(__name__)

# 教材存储（与graph.py共用）
DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / "data"
HISTORY_FILE = DATA_DIR / "textbooks.json"


def _load_textbooks() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.values():
            if item.get("status") == "parsing":
                item.update(status="failed", current_step="上次解析被中断", error="服务重启或进程退出，解析任务未完成")
        return data
    except Exception:
        logger.warning("教材历史读取失败，将使用空历史: %s", HISTORY_FILE, exc_info=True)
        return {}


_textbooks: dict = _load_textbooks()


def _save_textbooks():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(_textbooks, f, ensure_ascii=False)


def _next_textbook_id() -> str:
    nums = []
    for textbook_id in _textbooks:
        try:
            nums.append(int(textbook_id.rsplit("_", 1)[-1]))
        except ValueError:
            pass
    return f"book_{max(nums, default=0) + 1:03d}"


def update_textbook_status(textbook_id: str, **fields):
    """更新教材状态，后台任务和轮询接口共用。"""
    if textbook_id in _textbooks:
        _textbooks[textbook_id].update(fields)
        _save_textbooks()


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
    textbook_id = _next_textbook_id()

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
    _save_textbooks()

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
        batch_chars = max(1000, int(os.getenv("EXTRACT_BATCH_CHARS", "50000")))
        extraction_batches = create_extraction_batches(normalized_chapters, batch_chars)
        if not extraction_batches:
            raise ValueError("文件内容为空，无法提取知识点")
        update_textbook_status(
            textbook_id,
            progress=20,
            current_step=f"文件解析完成，共 {len(normalized_chapters)} 个内容片段，合并为 {len(extraction_batches)} 批提取"
        )

        concurrency = max(1, int(os.getenv("EXTRACT_CONCURRENCY", "3")))
        semaphore = asyncio.Semaphore(concurrency)
        completed = 0

        async def extract_one(index: int, batch: Chapter):
            nonlocal completed
            async with semaphore:
                update_textbook_status(
                    textbook_id,
                    progress=20 + int(65 * completed / len(extraction_batches)),
                    current_step=f"正在提取知识 {completed}/{len(extraction_batches)}（每批约 {batch_chars} 字，并发 {concurrency}）：{batch.title}"
                )
                result = await loop.run_in_executor(
                    None,
                    extractor.extract,
                    batch.content,
                    batch.title,
                    textbook_id
                )
                completed += 1
                update_textbook_status(
                    textbook_id,
                    progress=20 + int(65 * completed / len(extraction_batches)),
                    current_step=f"已提取知识 {completed}/{len(extraction_batches)}：{batch.title}"
                )
                return index, batch, result

        results = await asyncio.gather(*[
            extract_one(index, batch)
            for index, batch in enumerate(extraction_batches, start=1)
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
                page, chapter_title = infer_node_location(node, chapter)
                node["source"] = textbook_id
                node["chapter"] = chapter_title
                node["page"] = page
                all_nodes.append(node)

            for edge in result.get("edges", []):
                if not edge.get("source") or not edge.get("target"):
                    continue
                edge["source"] = node_ids.get(edge["source"], edge["source"])
                edge["target"] = node_ids.get(edge["target"], edge["target"])
                all_edges.append(edge)

        if not all_nodes:
            raise ValueError("知识提取未返回节点，请检查 LLM_API_BASE、LLM_MODEL 和 API Key 是否可用")

        extract_warning = None
        min_expected_nodes = max(20, min(300, total_chars // 3000))
        if len(all_nodes) < min_expected_nodes:
            extract_warning = f"知识点数量偏少：提取到 {len(all_nodes)} 个，建议检查模型输出或适当降低 EXTRACT_BATCH_CHARS"

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
        warning = extract_warning
        try:
            rag_service = get_rag_service()
            chunks = create_chunks(normalized_chapters, textbook_id)
            await loop.run_in_executor(None, rag_service.build_index, textbook_id, chunks)
        except Exception as e:
            warning = f"{warning}；RAG 索引失败：{e}" if warning else f"RAG 索引失败：{e}"
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


def create_extraction_batches(chapters: List[Chapter], max_chars: int) -> List[Chapter]:
    """把解析片段合并成大批次，减少 LLM 调用次数。"""
    segments = []
    for chapter in chapters:
        content = (chapter.content or "").strip()
        if not content:
            continue
        for part_index, start in enumerate(range(0, len(content), max_chars)):
            part = content[start:start + max_chars]
            suffix = f"-{part_index + 1}" if len(content) > max_chars else ""
            segments.append(Chapter(
                chapter_id=f"{chapter.chapter_id}{suffix}",
                title=f"{chapter.title}{suffix}",
                page_start=chapter.page_start,
                page_end=chapter.page_end,
                content=part,
                char_count=len(part)
            ))

    batches = []
    current = []
    current_len = 0

    def flush():
        if not current:
            return
        batch_index = len(batches)
        content = "\n\n".join(
            f"【片段 {i + 1}：{chapter.title}，页 {chapter.page_start}-{chapter.page_end}】\n{chapter.content}"
            for i, chapter in enumerate(current)
        )
        title = current[0].title if len(current) == 1 else f"{current[0].title} 等 {len(current)} 段"
        batches.append(Chapter(
            chapter_id=f"batch_{batch_index:03d}",
            title=title,
            page_start=current[0].page_start,
            page_end=current[-1].page_end,
            content=content,
            char_count=len(content)
        ))

    for chapter in segments:
        if current and current_len + chapter.char_count > max_chars:
            flush()
            current = []
            current_len = 0
        current.append(chapter)
        current_len += chapter.char_count

    flush()
    return batches


def infer_node_location(node: dict, batch: Chapter) -> tuple[int, str]:
    """从 LLM page 或批次片段标记推断节点页码。"""
    markers = [
        (m.start(), m.group(1), int(m.group(2)), int(m.group(3)))
        for m in re.finditer(r"【片段\s+\d+：(.+?)，页\s+(\d+)-(\d+)】", batch.content)
    ]

    page = parse_page(node.get("page"))
    if page:
        for _, title, start, end in markers:
            if start <= page <= end:
                return page, title
        return page, str(node.get("chapter") or batch.title)

    needle = str(node.get("name") or "").strip()
    if not needle:
        needle = str(node.get("definition") or "").strip()[:12]
    if needle:
        pos = batch.content.find(needle)
        if pos >= 0:
            selected = None
            for marker in markers:
                if marker[0] <= pos:
                    selected = marker
                else:
                    break
            if selected:
                _, title, start, _ = selected
                return max(1, start), title

    return max(1, batch.page_start), str(node.get("chapter") or batch.title)


def parse_page(value) -> int | None:
    if isinstance(value, int):
        return max(1, value)
    match = re.search(r"\d+", str(value or ""))
    return max(1, int(match.group(0))) if match else None


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
