"""
对话交互路由
职责：处理用户对话、修改整合决策
"""
import re
from fastapi import APIRouter
from typing import Dict, List
from app.models import ChatRequest, ChatResponse, ChatMessage

router = APIRouter()

# 模拟存储对话历史（按session_id分组）
_chat_histories: Dict[str, List[ChatMessage]] = {}


def _find_decision(decision_id: str):
    from app.routers.merge import _merge_decisions

    for decision in _merge_decisions:
        if decision.decision_id == decision_id:
            return decision
    return None


def _handle_message(message: str):
    from app.routers.merge import _merge_decisions

    match = re.search(r"(merge_\d+).*(改为|改成|设为|设置为)\s*(merge|keep|remove)", message, re.I)
    if match:
        decision = _find_decision(match.group(1))
        if not decision:
            return f"未找到决策 {match.group(1)}", None
        decision.action = match.group(3).lower()
        return f"已将 {decision.decision_id} 修改为 {decision.action}", f"{decision.decision_id} -> {decision.action}"

    match = re.search(r"(merge_\d+)", message, re.I)
    if match:
        decision = _find_decision(match.group(1))
        if not decision:
            return f"未找到决策 {match.group(1)}", None
        return (
            f"{decision.decision_id} 当前建议为 {decision.action}。"
            f"理由：{decision.reason}。置信度：{decision.confidence:.2f}",
            None
        )

    if not _merge_decisions:
        return "当前还没有整合决策。请先在整合面板选择至少 2 本已解析教材并开始整合。", None

    lines = [
        f"{d.decision_id}: {d.action}，置信度 {d.confidence:.2f}，{d.reason}"
        for d in _merge_decisions[:5]
    ]
    return "当前主要整合决策：\n" + "\n".join(lines), None


@router.post("")
@router.post("/")
async def chat(request: ChatRequest):
    """
    发送对话消息
    输入：用户消息和会话ID
    返回：系统回复和执行的操作
    """
    session_id = request.session_id or "default"

    # 初始化会话历史
    if session_id not in _chat_histories:
        _chat_histories[session_id] = []

    # 添加用户消息
    _chat_histories[session_id].append(
        ChatMessage(role="user", content=request.message)
    )

    reply, action_taken = _handle_message(request.message)

    # 添加助手回复
    _chat_histories[session_id].append(
        ChatMessage(role="assistant", content=reply)
    )

    return ChatResponse(reply=reply, action_taken=action_taken)


@router.get("/history")
async def get_chat_history(session_id: str = "default"):
    """
    获取对话历史
    返回：该会话的所有消息列表
    """
    return {
        "session_id": session_id,
        "messages": _chat_histories.get(session_id, [])
    }
