"""Eval Agent 配置模块

本模块使用 ``dataclass`` 定义三层配置，遍历优先级：命令行参数 > 环境变量 > 默认值。

配置层次::

    AgentConfig         ← 顶层聚合配置
    ├── LLMConfig       ← LLM 服务连接参数（API 地址 / 密钥 / 模型 / 温度）
    └── MemoryConfig    ← 记忆系统存储参数（目录 / 文件名 / 上限）

所有配置项均支持通过 ``EVAL_AGENT_*`` 环境变量覆盖，便于 CI/CD
与容器化部署场景下零改码切换。

环境变量一览:

    =========================  =======================================  ================
    环境变量                       说明                                     默认值
    =========================  =======================================  ================
    EVAL_AGENT_API_BASE        LLM API 端点                              localhost:11434
    EVAL_AGENT_API_KEY         API 密钥                                  ollama
    EVAL_AGENT_MODEL           模型名称                                  qwen3-coder:30b
    EVAL_AGENT_TEMPERATURE     采样温度 0‑1                                0.3
    EVAL_AGENT_MAX_TOKENS      单次最大生成 token                       8192
    EVAL_AGENT_TIMEOUT         HTTP 请求超时（秒）                        120
    EVAL_AGENT_MEMORY_DIR      记忆持久化目录                            ./memory_store
    =========================  =======================================  ================

作者: Jiangsheng Yu
License: MIT
"""

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM 服务连接配置

    Attributes:
        api_base:    API 端点地址，默认指向本地 Ollama 服务
        api_key:     API 密钥，Ollama 场景可使用任意值
        model:       模型名称，默认 qwen3-coder:30b
        temperature: 采样温度，越低越确定性（0‑1）
        max_tokens:  单次请求最大生成 token 数
        timeout:     HTTP 请求超时（秒）
    """
    api_base: str = os.getenv("EVAL_AGENT_API_BASE", "http://localhost:11434/v1")
    api_key: str = os.getenv("EVAL_AGENT_API_KEY", "ollama")
    model: str = os.getenv("EVAL_AGENT_MODEL", "qwen3-coder:30b")
    temperature: float = float(os.getenv("EVAL_AGENT_TEMPERATURE", "0.3"))
    max_tokens: int = int(os.getenv("EVAL_AGENT_MAX_TOKENS", "8192"))
    timeout: int = int(os.getenv("EVAL_AGENT_TIMEOUT", "120"))


@dataclass
class MemoryConfig:
    """记忆系统存储配置

    Attributes:
        memory_dir:            持久化文件所在目录
        long_term_file:        长期记忆 JSON 文件名
        knowledge_file:        持久知识库 JSON 文件名
        external_memory_file:  外部记忆 JSON 文件名（用户手动添加的笔记）
        max_long_term_entries:  长期记忆最大条目数；超出后按 LRU 淘汰
        max_relevant_memories:  单次检索返回的最大相关记忆条数
    """
    memory_dir: str = os.getenv(
        "EVAL_AGENT_MEMORY_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_store"),
    )
    long_term_file: str = "long_term_memory.json"
    knowledge_file: str = "persistent_knowledge.json"
    external_memory_file: str = "external_memory.json"
    max_long_term_entries: int = 500
    max_relevant_memories: int = 5


@dataclass
class AgentConfig:
    """Agent 顶层配置

    聚合 LLM 和记忆子配置，并提供全局开关。

    Attributes:
        llm:      LLM 服务配置
        memory:   记忆系统配置
        verbose:  启用详细日志（DEBUG 级别）
        language: 输出语言，zh=中文 / en=英文

    Example::

        # 最简用法：全部使用默认值
        config = AgentConfig()

        # 自定义 LLM + 详细日志
        config = AgentConfig(
            llm=LLMConfig(api_base="https://api.openai.com/v1", model="gpt-4o"),
            verbose=True,
        )
    """
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    verbose: bool = False
    language: str = "zh"
