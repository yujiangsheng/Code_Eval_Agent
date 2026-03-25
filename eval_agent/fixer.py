"""代码修复模块 — LLM 驱动的自动 Bug 修复

根据 Evaluator 输出的问题列表，生成修复后的完整代码。
每处修复均附带修复原因和信心评分（0-10），便于人工审查。
"""

from __future__ import annotations

import logging

from eval_agent.llm_client import LLMClient

logger = logging.getLogger(__name__)

FIXER_SYSTEM_PROMPT = """\
你是一个代码修复专家。你的任务是根据评估发现的问题，修复代码中的 Bug。

修复原则：
1. 每处修复必须说明原因
2. 修复后行为应与原始意图一致或更优
3. 不引入新的 Bug
4. 保持代码风格一致性
5. 优先修复严重问题

请严格按以下 JSON 格式输出：
```json
{
  "fixed_code": "修复后的完整代码",
  "fixes": [
    {
      "description": "修复了什么问题",
      "reason": "为什么需要修复",
      "original_line": 原始行号或null,
      "severity": "严重|中等|轻微"
    }
  ],
  "confidence": 0-10的修复信心分数,
  "notes": "修复说明或需要人工确认的事项"
}
```
"""


class Fixer:
    """LLM 驱动的代码修复器

    接收原始源码和 issue 列表，输出修复后代码与修复清单。
    修复原则：只修必须修的、不引入新 Bug、保持原有风格。
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def fix(self, source: str, issues: list[dict], code_graph: str = "") -> dict:
        """根据问题列表修复代码

        Args:
            source: 原始源代码
            issues: 评估发现的问题列表
            code_graph: 代码结构图

        Returns:
            修复结果字典
        """
        user_prompt = self._build_prompt(source, issues, code_graph)
        return self.llm.chat_json(FIXER_SYSTEM_PROMPT, user_prompt)

    def _build_prompt(self, source: str, issues: list[dict], code_graph: str) -> str:
        parts = ["请修复以下代码中发现的问题：\n"]
        parts.append(f"```python\n{source}\n```\n")

        if issues:
            parts.append("发现的问题：")
            for i, issue in enumerate(issues, 1):
                severity = issue.get("severity", "未知")
                desc = issue.get("description", "")
                suggestion = issue.get("suggestion", "")
                line = issue.get("line")
                line_str = f" (行 {line})" if line else ""
                parts.append(f"  {i}. [{severity}]{line_str} {desc}")
                if suggestion:
                    parts.append(f"     建议：{suggestion}")

        if code_graph:
            parts.append(f"\n代码结构：\n{code_graph}")

        return "\n".join(parts)
