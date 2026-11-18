# pip install openai>=1.0.0 tenacity aiolimiter httpx
import asyncio
from typing import Any, Dict, List, Optional
import re
from aiolimiter import AsyncLimiter
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)
from openai import AsyncOpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError, APIStatusError
import os
import httpx

def _is_retryable_status(exc: Exception) -> bool:
    """对 429 / 5xx 的状态异常进行重试。"""
    return isinstance(exc, APIStatusError) and (exc.status_code == 429 or 500 <= exc.status_code < 600)


_RETRY_COND = (
    retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError))
    | retry_if_exception(_is_retryable_status)
)


class GPT5ChatClient:
    """
    异步 Chat Completions 客户端封装，带并发控制 / 限流 / 重试。
    """
        
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        max_concurrency: int = 512,
        rps: Optional[int] = 100,
        rps_period: float = 1.0,
        default_timeout: float = 300.0,
        model: str = "deepseek-ai/DeepSeek-V3.1-Terminus"
    ):    
        # 优先从环境变量读取，如果没有则为 None
        env_base_url = os.getenv("CHAT_API_BASE", None)
        env_api_key = os.getenv("CHAT_API_KEY", None)
        env_model = os.getenv("CHAT_MODEL_NAME", None)

        # 参数优先级：传入参数 > 环境变量
        self.base_url = base_url or env_base_url
        self.api_key = api_key or env_api_key
        # 注意：这里如果传入了 model 参数，优先用传入的，否则用环境变量的，否则用默认值
        self.model = model if model != "deepseek-ai/DeepSeek-V3.1-Terminus" else (env_model or model)
        
        assert self.api_key, "API key must be provided via argument or CHAT_API_KEY env var"
        assert self.base_url, "Base URL must be provided via argument or CHAT_API_BASE env var"
        
        self.rps = rps        
        
       
        http_client = httpx.AsyncClient(
            timeout=600, 
            trust_env=False  
        )
        
        self._sdk = AsyncOpenAI(
            api_key=self.api_key, 
            base_url=self.base_url,
            http_client=http_client
        )
        
        self._sem = asyncio.Semaphore(max_concurrency)
        self._limiter = AsyncLimiter(max_rate=rps, time_period=rps_period) if rps else None
        self._default_timeout = default_timeout

    async def __aenter__(self) -> "GPT5ChatClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        pass
    
    def _strip_fences(self, s: str) -> str:
        """剥掉 ```json ... ``` 或 ``` ... ``` 代码围栏；若无则原样返回。"""
        if not isinstance(s, str):
            return s
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
        return (m.group(1) if m else s).strip()

    # ---- 公共方法 ---------------------------------------------------------

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        *,
        response_format: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 6,
        **extra_kwargs: Any,
    ):
        """
        发送一次 Chat Completion 调用（带重试）。
        """
        @retry(
            retry=_RETRY_COND,
            stop=stop_after_attempt(max_retries),
            wait=wait_random_exponential(min=1, max=60),
            reraise=True,
        )
        async def _do_call():
            if self._limiter is not None:
                async with self._limiter:
                    pass
                
            async with self._sem:
                return await self._sdk.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format=response_format,
                    timeout=timeout or self._default_timeout,
                    **extra_kwargs,
                )

        return await _do_call()

    async def chat_text(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """
        便捷方法：直接返回第一条 choice 的 message.content。
        """
        resp = await self.chat_completion(messages, **kwargs)
        
        if not resp.choices or not getattr(resp.choices[0], "message", None):
            raise RuntimeError(f"Unexpected response shape: {resp}")
        
        response = resp.choices[0].message.content or ""
        response = self._strip_fences(response)
        
        return response.strip()

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        *,
        response_format: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 6,
        **extra_kwargs: Any,
    ):
        """
        流式（server-sent events）接口。
        """
        @retry(
            retry=_RETRY_COND,
            stop=stop_after_attempt(max_retries),
            wait=wait_random_exponential(min=1, max=60),
            reraise=True,
        )
        async def _open_stream():
            if self._limiter is not None:
                async with self._limiter:
                    pass
            async with self._sem:
                return await self._sdk.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format=response_format,
                    timeout=timeout or self._default_timeout,
                    stream=True,
                    **extra_kwargs,
                )

        stream = await _open_stream()
        async for chunk in stream:
            yield chunk

    @staticmethod
    def to_user_text(resp) -> str:
        """从标准响应中提取首条文本内容。"""
        try:
            return resp.choices[0].message.content or ""
        except Exception:
            raise RuntimeError(f"Unexpected response shape: {resp}")