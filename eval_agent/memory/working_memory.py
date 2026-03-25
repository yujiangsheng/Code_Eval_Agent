"""工作记忆 — 单轮任务生命周期内的上下文存储

WorkingMemory 作为 EvalAgent 单次评估任务的"黑板"，
在流水线各步骤间传递中间结果:

    source_code → ast_info / code_graph → evaluation / issues
    → fixed_code → improved_code → test_cases → experience_summary

每次新任务开始时调用 reset() 清空，任务结束后通过
经验总结步骤将有价值的信息提取到长期记忆。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WorkingMemory:
    """工作记忆：保存当前任务的上下文信息

    生命周期：单轮任务，任务结束后可选择性地提取经验到长期记忆。
    """

    source_code: str = ""
    file_path: Optional[str] = None
    language: str = "python"

    # 分析产出
    ast_info: dict = field(default_factory=dict)
    code_graph: str = ""
    static_analysis: dict = field(default_factory=dict)

    # 评估结果
    evaluation: dict = field(default_factory=dict)
    issues: list[dict] = field(default_factory=list)

    # 修复与改进
    fixed_code: str = ""
    improved_code: str = ""
    improvements: list[str] = field(default_factory=list)

    # 验证
    test_cases: list[str] = field(default_factory=list)

    # 经验总结
    experience_summary: str = ""

    # 额外上下文
    context: dict[str, Any] = field(default_factory=dict)

    def reset(self):
        """重置工作记忆（新任务开始时）"""
        self.source_code = ""
        self.file_path = None
        self.language = "python"
        self.ast_info = {}
        self.code_graph = ""
        self.static_analysis = {}
        self.evaluation = {}
        self.issues = []
        self.fixed_code = ""
        self.improved_code = ""
        self.improvements = []
        self.test_cases = []
        self.experience_summary = ""
        self.context = {}

    def summary(self) -> str:
        """返回工作记忆的简要文字摘要，供 LLM 参考"""
        parts = []
        if self.file_path:
            parts.append(f"文件：{self.file_path}")
        parts.append(f"语言：{self.language}")
        parts.append(f"代码长度：{len(self.source_code)} 字符")
        if self.code_graph:
            parts.append(f"Code Graph：\n{self.code_graph}")
        if self.issues:
            severity_count = {}
            for issue in self.issues:
                s = issue.get("severity", "未知")
                severity_count[s] = severity_count.get(s, 0) + 1
            parts.append(f"已发现问题：{severity_count}")
        return "\n".join(parts)
