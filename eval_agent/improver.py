"""代码改进模块 — 重构、性能优化、结构优化、可读性提升

在 Fixer 修复后的代码基础上进一步提升质量。
改进遵循"功能不变"原则，每条改进都附带类型标签和影响说明。
"""

from __future__ import annotations

import logging

from eval_agent.llm_client import LLMClient

logger = logging.getLogger(__name__)

IMPROVER_SYSTEM_PROMPT = """\
你是一个代码改进专家。在修复后的代码基础上，进一步提升代码质量。

改进方向：
1. **重构（Refactor）**：提取函数、消除重复、优化命名
2. **性能优化**：算法优化、数据结构选择、缓存策略
3. **结构优化**：模块化、解耦、职责单一
4. **可读性提升**：清晰的命名、合理的注释、一致的风格

改进要求：
- 保持功能不变
- 遵循 Python 最佳实践
- 每个改进点必须有清晰的说明

请严格按以下 JSON 格式输出：
```json
{
  "improved_code": "改进后的完整代码",
  "improvements": [
    {
      "type": "refactor|performance|structure|readability",
      "description": "改进内容描述",
      "impact": "改进带来的效果"
    }
  ],
  "before_after_summary": "改进前后的关键差异总结"
}
```
"""


class Improver:
    """LLM 驱动的代码改进器

    改进方向包括 refactor / performance / structure / readability，
    输出改进后代码与逐条改进说明。
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def improve(
        self,
        source: str,
        evaluation: dict,
        code_graph: str = "",
        relevant_knowledge: str = "",
    ) -> dict:
        """对代码进行改进

        Args:
            source: （已修复的）源代码
            evaluation: 评估结果
            code_graph: 代码结构图
            relevant_knowledge: 相关知识库内容

        Returns:
            改进结果字典
        """
        user_prompt = self._build_prompt(source, evaluation, code_graph, relevant_knowledge)
        return self.llm.chat_json(IMPROVER_SYSTEM_PROMPT, user_prompt)

    def _build_prompt(
        self, source: str, evaluation: dict, code_graph: str, knowledge: str
    ) -> str:
        parts = ["请改进以下代码：\n"]
        parts.append(f"```python\n{source}\n```\n")

        # 附加评估维度信息
        dims = evaluation.get("dimensions", {})
        if dims:
            parts.append("当前评估得分：")
            for dim, info in dims.items():
                score = info.get("score", "N/A")
                comment = info.get("comment", "")
                parts.append(f"  - {dim}: {score}/10 - {comment}")

        if code_graph:
            parts.append(f"\n代码结构：\n{code_graph}")

        if knowledge:
            parts.append(f"\n参考知识：\n{knowledge}")

        return "\n".join(parts)
