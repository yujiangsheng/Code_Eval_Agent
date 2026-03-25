"""记忆系统模块 — 四层记忆架构

设计理念源自认知科学的记忆模型，将知识按生命周期和来源分层存储。

层级结构::

    工作记忆 (WorkingMemory)        ← 单轮任务上下文（代码、AST、评估结果）
    长期记忆 (LongTermMemory)       ← 跨任务经验积累（Bug 模式 / 优化策略）
    持久知识 (PersistentKnowledge)  ← 内置最佳实践（PEP 8 / 安全清单 / 常见陷阱）
    外部记忆 (external_memory.json)  ← 用户手动添加的笔记与参考上下文

记忆流转::

    任务开始 → 初始化工作记忆
      → 各步骤写入中间结果
      → 任务结束时提炼经验
      → 写入长期记忆（JSON 持久化）
      → 后续任务检索相关经验
"""

from eval_agent.memory.working_memory import WorkingMemory
from eval_agent.memory.long_term_memory import LongTermMemory
from eval_agent.memory.persistent_knowledge import PersistentKnowledge

__all__ = ["WorkingMemory", "LongTermMemory", "PersistentKnowledge"]
