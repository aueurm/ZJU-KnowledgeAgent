"""
LLM客户端服务
职责：封装LLM API调用，统一管理
"""
import asyncio
import os
import time
from typing import Optional
from dotenv import load_dotenv
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError, AsyncOpenAI, OpenAI

load_dotenv()


class LLMClient:
    """LLM统一客户端（支持多种后端）"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "deepseek-v4-flash"):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LLM_API_BASE", "https://api.deepseek.com")).rstrip("/")
        self.model = os.getenv("LLM_MODEL", model)
        self.timeout = float(os.getenv("LLM_TIMEOUT", "120"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.thinking = os.getenv("LLM_THINKING", "disabled")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout, max_retries=0)
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout, max_retries=0)

    async def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[dict] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        调用LLM生成文本
        输入：用户Prompt、可选的系统Prompt、温度参数
        返回：生成的文本
        """
        if not self.api_key or self.api_key == "your_api_key_here":
            return "LLM调用失败: 请先设置有效的 LLM_API_KEY"

        kwargs = self._request_kwargs(prompt, system_prompt, temperature, response_format, max_tokens)
        for attempt in range(self.max_retries):
            try:
                response = await self.async_client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as exc:
                if attempt == self.max_retries - 1 or not self._should_retry(exc):
                    return f"LLM调用失败: {self._format_error(exc)}"
                await asyncio.sleep(2 ** attempt)

    def call_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[dict] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """同步版本的LLM调用"""
        if not self.api_key or self.api_key == "your_api_key_here":
            return "LLM调用失败: 请先设置有效的 LLM_API_KEY"

        kwargs = self._request_kwargs(prompt, system_prompt, temperature, response_format, max_tokens)
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as exc:
                if attempt == self.max_retries - 1 or not self._should_retry(exc):
                    return f"LLM调用失败: {self._format_error(exc)}"
                time.sleep(2 ** attempt)

    def _request_kwargs(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        response_format: Optional[dict],
        max_tokens: Optional[int],
    ) -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if "deepseek" in self.base_url.lower() and self.thinking:
            kwargs["extra_body"] = {"thinking": {"type": self.thinking}}
        if response_format:
            kwargs["response_format"] = response_format
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        return kwargs

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, (APIConnectionError, APITimeoutError)):
            return True
        if isinstance(exc, APIStatusError):
            return exc.status_code in {408, 409, 429, 500, 502, 503, 504}
        message = str(exc).lower()
        return "response ended prematurely" in message or "connection" in message or "timeout" in message

    def _format_error(self, exc: Exception) -> str:
        if isinstance(exc, APIStatusError):
            return f"HTTP {exc.status_code}: {exc.message}"
        if isinstance(exc, APIError):
            return exc.message
        return str(exc)


# 全局LLM客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取LLM客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
