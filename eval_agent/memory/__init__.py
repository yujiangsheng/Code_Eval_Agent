"""记忆系统模块 — 三层记忆架构

层级结构::

    工作记忆 (WorkingMemory)
      ├─ 生命周期：单轮任务
      └─ 内容：当前代码、AST、Code Graph、评估上下文

    长期记忆 (LongTermMemory)
      ├─ 生命周期：跨任务持久化（JSON 文件）
      └─ 内容：Bug 模式、优化策略、代码结构经验

    持久知识 (PersistentKnowledge)
      ├─ 生命周期：永久
      └─ 内容：PEP 8 规范、安全清单、常见陷阱等内置知识
"""

from eval_agent.memory.working_memory import WorkingMemory
from eval_agent.memory.long_term_memory import LongTermMemory
from eval_agent.memory.persistent_knowledge import PersistentKnowledge

__all__ = ["WorkingMemory", "LongTermMemory", "PersistentKnowledge"]
