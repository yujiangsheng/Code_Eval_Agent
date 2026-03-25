"""LLM 客户端 — 兼容 OpenAI API 的统一调用封装

本模块封装了 OpenAI Python SDK，支持所有兼容 OpenAI Chat Completions
接口的服务端（Ollama、vLLM、LiteLLM 等）。

主要功能:
  - chat()      : 发送对话请求，返回纯文本
  - chat_json() : 发送对话请求，自动从回复中提取并解析 JSON

使用示例::

    from config import LLMConfig
    from eval_agent.llm_client import LLMClient

    client = LLMClient(LLMConfig())
    text = client.chat("你是一个助手", "你好")
    data = client.chat_json("你是一个助手", "请输出JSON")
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from openai import OpenAI

from config import LLMConfig

logger = logging.getLogger(__name__)

# 用于从 LLM 回复中提取 JSON 代码块的正则
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


class LLMClient:
    """通过 OpenAI 兼容 API 与大语言模型交互

    Attributes:
        config: LLM 连接配置
        client: OpenAI SDK 客户端实例
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(
            base_url=config.api_base,
            api_key=config.api_key,
            timeout=config.timeout,
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """发送对话请求并返回模型生成的文本

        Args:
            system_prompt: 系统提示词（角色设定）
            user_prompt:   用户消息
            temperature:   采样温度，为 None 时使用配置默认值
            max_tokens:    最大生成 token 数，为 None 时使用配置默认值

        Returns:
            模型回复的文本内容

        Raises:
            Exception: 当 API 调用失败时原样抛出
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )
            content = response.choices[0].message.content or ""
            logger.debug("LLM 响应长度: %d 字符", len(content))
            return content
        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            raise

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> dict:
        """发送请求并解析模型回复中的 JSON

        解析策略（按优先级）:
          1. 提取 ```json ... ``` 或 ``` ... ``` 代码块
          2. 直接对整体回复做 json.loads

        Args:
            system_prompt: 系统提示词
            user_prompt:   用户消息
            temperature:   采样温度

        Returns:
            解析后的 dict；若解析失败则返回 {"raw_response": ...}
        """
        raw = self.chat(system_prompt, user_prompt, temperature)

        # 尝试提取 JSON 代码块
        match = _JSON_BLOCK_RE.search(raw)
        json_text = match.group(1).strip() if match else raw.strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning("JSON 解析失败，返回原始文本")
            return {"raw_response": raw}
