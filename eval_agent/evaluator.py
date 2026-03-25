"""代码评估模块 — LLM 驱动的多维度代码质量评估

评估维度（7 项）:
  1. 语法正确性     2. 逻辑正确性     3. 边界条件
  4. 时间/空间复杂度  5. 安全性         6. 代码规范
  7. 可维护性

输出格式: JSON dict，包含 overall_score（0-10）、dimensions 和 issues 列表。
"""

from __future__ import annotations

import logging

from eval_agent.llm_client import LLMClient
from eval_agent.analyzer import AnalysisResult

logger = logging.getLogger(__name__)

EVALUATION_SYSTEM_PROMPT = """\
你是一个专业的代码评估专家。请对给定代码进行全面的多维度评估。

评估维度：
1. **语法正确性**：代码是否存在语法错误
2. **逻辑正确性**：算法是否正确，逻辑是否合理
3. **边界条件**：是否覆盖了常见的边界情况（空输入、极端值、异常数据等）
4. **时间/空间复杂度**：算法复杂度分析和优化空间
5. **安全性**：是否存在注入、信息泄露等安全漏洞
6. **代码规范**：是否遵循 PEP 8 等编码规范
7. **可维护性**：代码结构是否清晰，是否易于扩展

请严格按以下 JSON 格式输出：
```json
{
  "overall_score": 0-10的整数评分,
  "dimensions": {
    "syntax": {"score": 0-10, "comment": "说明"},
    "logic": {"score": 0-10, "comment": "说明"},
    "boundary": {"score": 0-10, "comment": "说明"},
    "complexity": {"score": 0-10, "comment": "说明", "time": "O(?)", "space": "O(?)"},
    "security": {"score": 0-10, "comment": "说明"},
    "style": {"score": 0-10, "comment": "说明"},
    "maintainability": {"score": 0-10, "comment": "说明"}
  },
  "issues": [
    {
      "severity": "严重|中等|轻微",
      "type": "bug|performance|security|style|design",
      "line": 行号或null,
      "description": "问题描述",
      "suggestion": "修复建议"
    }
  ],
  "summary": "总体评价，一两句话概括"
}
```
"""


class Evaluator:
    """LLM 驱动的多维度代码评估器

    将源代码及其静态分析结果组装为 prompt，由 LLM 输出结构化评估。
    评估结果按严重性排序后供后续 Fixer / Improver 消费。
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def evaluate(self, source: str, analysis: AnalysisResult) -> dict:
        """对代码进行多维度评估

        Args:
            source: 源代码
            analysis: 静态分析结果

        Returns:
            评估结果字典
        """
        user_prompt = self._build_prompt(source, analysis)
        result = self.llm.chat_json(EVALUATION_SYSTEM_PROMPT, user_prompt)

        # 确保 issues 列表按严重性排序
        if "issues" in result:
            severity_order = {"严重": 0, "中等": 1, "轻微": 2}
            result["issues"].sort(
                key=lambda x: severity_order.get(x.get("severity", "轻微"), 3)
            )

        return result

    def _build_prompt(self, source: str, analysis: AnalysisResult) -> str:
        """构建评估提示，将源码和静态分析指标整合到用户 prompt 中"""
        parts = ["请评估以下 Python 代码：\n"]
        parts.append(f"```python\n{source}\n```\n")

        # 附加静态分析信息
        info = analysis.to_dict()
        metrics = info["metrics"]
        parts.append(f"代码指标：{metrics['total_lines']} 行（有效代码 {metrics['code_lines']} 行，注释 {metrics['comment_lines']} 行）")

        if analysis.syntax_errors:
            parts.append(f"\n已知语法错误：{analysis.syntax_errors}")

        if analysis.code_graph:
            parts.append(f"\nCode Graph：\n{analysis.code_graph}")

        # 复杂度信息
        complex_funcs = [f for f in analysis.functions if f.complexity > 5]
        if complex_funcs:
            parts.append("\n高复杂度函数：")
            for f in complex_funcs:
                name = f"{f.class_name}.{f.name}" if f.class_name else f.name
                parts.append(f"  - {name}: 圈复杂度={f.complexity}")

        return "\n".join(parts)
