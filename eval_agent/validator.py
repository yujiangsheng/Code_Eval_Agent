"""代码验证模块 — 自动生成 pytest 测试用例

根据代码的函数签名和类结构自动生成四类测试:
  - normal:      正常路径测试
  - boundary:    边界条件测试
  - exception:   异常路径测试
  - performance: 性能基准测试（如适用）

输出包含可直接运行的 pytest 代码和测试用例摘要。
"""

from __future__ import annotations

import logging

from eval_agent.llm_client import LLMClient
from eval_agent.analyzer import AnalysisResult

logger = logging.getLogger(__name__)

VALIDATOR_SYSTEM_PROMPT = """\
你是一个测试专家，擅长多种编程语言的测试框架。请为给定代码生成全面的测试用例。

测试要求：
1. **正常路径测试**：常规输入的正确输出
2. **边界测试**：空输入、极值、极端情况
3. **异常路径测试**：错误输入、异常触发
4. **性能测试**（如适用）：大数据量场景

测试框架：请根据代码语言选择合适的测试框架

请严格按以下 JSON 格式输出：
```json
{
  "test_code": "完整的pytest测试代码",
  "test_cases": [
    {
      "name": "测试函数名",
      "category": "normal|boundary|exception|performance",
      "description": "测试内容描述"
    }
  ],
  "coverage_notes": "测试覆盖说明"
}
```
"""


class Validator:
    """LLM 驱动的测试用例生成器

    分析函数签名与类结构后，由 LLM 生成覆盖四类场景的 pytest 代码。
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_tests(self, source: str, analysis: AnalysisResult, lang_name: str = "Python", lang_id: str = "python", test_framework: str = "pytest") -> dict:
        """为代码生成测试用例

        Args:
            source: 源代码（建议为改进后的版本）
            analysis: 代码分析结果

        Returns:
            测试用例字典
        """
        user_prompt = self._build_prompt(source, analysis, lang_name, lang_id, test_framework)
        return self.llm.chat_json(VALIDATOR_SYSTEM_PROMPT, user_prompt)

    def _build_prompt(self, source: str, analysis: AnalysisResult, lang_name: str = "Python", lang_id: str = "python", test_framework: str = "pytest") -> str:
        parts = [f"请为以下 {lang_name} 代码生成测试用例（使用 {test_framework} 测试框架）：\n"]
        parts.append(f"```{lang_id}\n{source}\n```\n")

        # 提供函数签名信息
        if analysis.functions:
            parts.append("函数列表：")
            for f in analysis.functions:
                prefix = f"{f.class_name}." if f.class_name else ""
                parts.append(f"  - {prefix}{f.name}({', '.join(f.args)})")
                if f.docstring:
                    parts.append(f"    文档: {f.docstring[:100]}")

        # 提供类信息
        if analysis.classes:
            parts.append("\n类列表：")
            for c in analysis.classes:
                parts.append(f"  - {c.name}: 方法 {c.methods}")

        return "\n".join(parts)
