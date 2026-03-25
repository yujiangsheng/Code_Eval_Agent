"""Eval Agent 主编排器 — 串联全部评估流程

本模块是 Eval Agent 的中枢调度器，负责：
  - 单文件模式：9 步流水线（解析 → 评估 → 修复 → 改进 → 验证 → 经验总结）
  - 目录模式：递归扫描 → 跨文件分析 → LLM 深度解读 → 关键文件评估

核心类：
  - EvalAgent : 顶层 Agent，对外暴露 run() / run_directory() / run_with_check()

依赖模块::

    CodeAnalyzer → Evaluator → Fixer → Improver → Validator
         ↑                                            |
         └─── WorkingMemory / LongTermMemory / PersistentKnowledge ──┘
"""

from __future__ import annotations

import logging
from typing import Optional

from config import AgentConfig
from eval_agent.llm_client import LLMClient
from eval_agent.analyzer import CodeAnalyzer
from eval_agent.evaluator import Evaluator
from eval_agent.fixer import Fixer
from eval_agent.improver import Improver
from eval_agent.validator import Validator
from eval_agent.formatter import OutputFormatter
from eval_agent.scanner import DirectoryScanner, ProjectAnalysis, FileAnalysis
from eval_agent.memory import WorkingMemory, LongTermMemory, PersistentKnowledge

logger = logging.getLogger(__name__)

EXPERIENCE_SYSTEM_PROMPT = """\
你是一个经验提炼专家。请根据本次代码评估任务的全过程，总结可复用的经验。

总结要求：
1. 提炼出通用的 Bug 模式（如果有）
2. 总结有效的优化策略
3. 记录代码结构方面的教训
4. 用简洁的语言描述，每条经验不超过一句话

请严格按以下 JSON 格式输出：
```json
{
  "experience_text": "可读的经验总结文本",
  "entries": [
    {
      "category": "bug_pattern|optimization|structure|general",
      "content": "经验内容",
      "tags": ["标签1", "标签2"]
    }
  ]
}
```
"""


class EvalAgent:
    """Eval Agent — 面向代码的评估与进化型智能体

    单文件工作流程（9 步）::

        ┌──────────────────────────────────────────────┐
        │ 1. 解析输入代码（AST）                        │
        │ 2. 构建结构视图（Code Graph）                 │
        │ 3. 执行多维评估（7 维度，输出 issues 列表）    │
        │ 4. 问题清单（按严重性排序）                    │
        │ 5. 修复方案（仅中等/严重级别触发）             │
        │ 6. 代码改进（refactor/performance/structure）  │
        │ 7. 优化说明                                   │
        │ 8. 生成 pytest 测试用例                       │
        │ 9. 提炼经验 → 写入长期记忆                    │
        └──────────────────────────────────────────────┘

    目录工作流程:
        scan → LLM 深度解读 → 选取关键文件逐一评估 → 经验总结

    Attributes:
        config:          AgentConfig 配置实例
        llm:             LLMClient 客户端
        analyzer:        CodeAnalyzer 静态分析器
        evaluator:       Evaluator 评估器
        fixer:           Fixer 修复器
        improver:        Improver 改进器
        validator:       Validator 测试生成器
        formatter:       OutputFormatter 输出格式化器
        working_memory:  WorkingMemory 工作记忆
        long_term_memory:LongTermMemory 长期记忆
        knowledge:       PersistentKnowledge 持久知识库
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()

        # 初始化 LLM 客户端
        self.llm = LLMClient(self.config.llm)

        # 初始化各模块
        self.analyzer = CodeAnalyzer()
        self.evaluator = Evaluator(self.llm)
        self.fixer = Fixer(self.llm)
        self.improver = Improver(self.llm)
        self.validator = Validator(self.llm)
        self.formatter = OutputFormatter()

        # 初始化记忆系统
        self.working_memory = WorkingMemory()
        self.long_term_memory = LongTermMemory(self.config.memory)
        self.knowledge = PersistentKnowledge(self.config.memory)

    def run(self, source: str, file_path: Optional[str] = None) -> str:
        """执行完整的评估流程

        Args:
            source: 待评估的源代码
            file_path: 源文件路径（可选）

        Returns:
            格式化的评估报告
        """
        # —— 步骤 0：初始化工作记忆 ——
        self.working_memory.reset()
        self.working_memory.source_code = source
        self.working_memory.file_path = file_path
        logger.info("开始评估%s", f" [{file_path}]" if file_path else "")

        # —— 步骤 1 & 2：解析代码 + 构建 Code Graph ——
        self._step_analyze(source, file_path)

        # —— 步骤 3：多维评估 ——
        self._step_evaluate(source)

        # —— 步骤 4 & 5：修复 ——
        fix_result = self._step_fix(source)

        # —— 步骤 6 & 7：改进 ——
        code_to_improve = fix_result.get("fixed_code", source) if fix_result else source
        improve_result = self._step_improve(code_to_improve)

        # —— 步骤 8：测试用例生成 ——
        final_code = (
            improve_result.get("improved_code", code_to_improve)
            if improve_result
            else code_to_improve
        )
        test_result = self._step_validate(final_code)

        # —— 步骤 9：经验总结与记忆更新 ——
        experience = self._step_summarize_experience()

        # —— 格式化输出 ——
        analysis = self._get_analysis_from_working_memory()
        report = self.formatter.format(
            evaluation=self.working_memory.evaluation,
            analysis=analysis,
            fix_result=fix_result,
            improve_result=improve_result,
            test_result=test_result,
            experience=experience,
        )

        logger.info("评估完成")
        return report

    def _step_analyze(self, source: str, file_path: Optional[str]):
        """步骤 1 & 2：静态分析 + Code Graph"""
        logger.info("[1/9] 解析代码与构建 Code Graph...")
        analysis = self.analyzer.analyze(source, filename=file_path or "<input>")
        self.working_memory.ast_info = analysis.to_dict()
        self.working_memory.code_graph = analysis.code_graph
        self.working_memory.static_analysis = analysis.to_dict()

        if analysis.syntax_errors:
            logger.warning("发现语法错误: %s", analysis.syntax_errors)

    def _step_evaluate(self, source: str):
        """步骤 3：多维评估"""
        logger.info("[2/9] 执行多维评估...")
        analysis = self._get_analysis_from_working_memory()

        # 检索相关长期记忆
        keywords = self._extract_keywords(source)
        relevant_memories = self.long_term_memory.search(keywords=keywords)
        if relevant_memories:
            logger.info("找到 %d 条相关历史经验", len(relevant_memories))

        evaluation = self.evaluator.evaluate(source, analysis)
        self.working_memory.evaluation = evaluation
        self.working_memory.issues = evaluation.get("issues", [])

        score = evaluation.get("overall_score", "N/A")
        n_issues = len(self.working_memory.issues)
        logger.info("评估完成：总分 %s/10，发现 %d 个问题", score, n_issues)

    def _step_fix(self, source: str) -> Optional[dict]:
        """步骤 4 & 5：修复"""
        issues = self.working_memory.issues
        # 仅当存在中等及以上严重性的问题时才执行修复
        needs_fix = any(
            i.get("severity") in ("严重", "中等") for i in issues
        )
        if not needs_fix:
            logger.info("[3/9] 无需修复，跳过")
            return None

        logger.info("[3/9] 执行代码修复...")
        fix_result = self.fixer.fix(
            source, issues, self.working_memory.code_graph
        )
        self.working_memory.fixed_code = fix_result.get("fixed_code", source)
        return fix_result

    def _step_improve(self, source: str) -> Optional[dict]:
        """步骤 6 & 7：改进"""
        logger.info("[4/9] 执行代码改进...")
        # 获取相关知识
        keywords = self._extract_keywords(source)
        relevant_knowledge = self.knowledge.get_relevant(keywords)

        improve_result = self.improver.improve(
            source,
            self.working_memory.evaluation,
            self.working_memory.code_graph,
            relevant_knowledge,
        )
        self.working_memory.improved_code = improve_result.get("improved_code", source)
        self.working_memory.improvements = [
            imp.get("description", "")
            for imp in improve_result.get("improvements", [])
        ]
        return improve_result

    def _step_validate(self, source: str) -> Optional[dict]:
        """步骤 8：生成测试用例"""
        logger.info("[5/9] 生成测试用例...")
        analysis = self.analyzer.analyze(source)
        test_result = self.validator.generate_tests(source, analysis)
        self.working_memory.test_cases = test_result.get("test_cases", [])
        return test_result

    def _step_summarize_experience(self) -> str:
        """步骤 9：经验总结与记忆更新"""
        logger.info("[6/9] 总结经验...")
        context = (
            f"代码评分：{self.working_memory.evaluation.get('overall_score', 'N/A')}/10\n"
            f"发现问题数：{len(self.working_memory.issues)}\n"
            f"改进项数：{len(self.working_memory.improvements)}\n"
        )
        if self.working_memory.issues:
            context += "问题类型：" + ", ".join(
                set(i.get("type", "") for i in self.working_memory.issues)
            ) + "\n"
        if self.working_memory.improvements:
            context += "改进方向：" + ", ".join(self.working_memory.improvements[:5]) + "\n"

        user_prompt = f"请根据以下评估结果总结经验：\n{context}"
        result = self.llm.chat_json(EXPERIENCE_SYSTEM_PROMPT, user_prompt)

        # 存储经验到长期记忆
        entries = result.get("entries", [])
        for entry in entries:
            self.long_term_memory.add(
                category=entry.get("category", "general"),
                content=entry.get("content", ""),
                tags=entry.get("tags", []),
                source_file=self.working_memory.file_path,
            )
        if entries:
            logger.info("新增 %d 条长期记忆", len(entries))

        experience = result.get("experience_text", "")
        self.working_memory.experience_summary = experience
        return experience

    def _get_analysis_from_working_memory(self):
        """从工作记忆还原 AnalysisResult（用于格式化等场景）"""
        return self.analyzer.analyze(
            self.working_memory.source_code,
            filename=self.working_memory.file_path or "<input>",
        )

    def _extract_keywords(self, source: str) -> list[str]:
        """从代码中提取关键词用于记忆检索"""
        import re
        # 提取函数名、类名和常见模式
        names = re.findall(r'\bdef\s+(\w+)', source)
        names += re.findall(r'\bclass\s+(\w+)', source)
        # 提取导入模块名
        names += re.findall(r'\bimport\s+(\w+)', source)
        names += re.findall(r'\bfrom\s+(\w+)', source)
        # 去重并过滤太短的名字
        return list(set(n for n in names if len(n) > 2))


    # ---- 自我校验 ----

    def self_check(self, report: str) -> str:
        """自我校验机制 — 在输出前由 LLM 审核报告质量

        检查项:
          - 是否遗漏了重要问题?
          - 修复方案是否可能引入新 Bug?
          - 建议是否符合 Python 最佳实践?
          - 是否存在更优的解决方案?
        """
        check_prompt = f"""\
请对以下代码评估报告进行自检：

{report}

检查项：
1. 是否遗漏了重要问题？
2. 修复方案是否可能引入新的 Bug？
3. 改进建议是否符合 Python 最佳实践？
4. 是否存在更优的解决方案？

如果发现问题，请指出；如果没有，请确认报告质量合格。
简要输出检查结论。
"""
        return self.llm.chat(
            "你是一个代码评审质检员，负责审核代码评估报告的完整性和准确性。",
            check_prompt,
        )

    def run_with_check(self, source: str, file_path: Optional[str] = None) -> str:
        """执行评估并附加自我校验"""
        report = self.run(source, file_path)
        logger.info("[7/9] 执行自我校验...")
        check_result = self.self_check(report)
        return report + f"\n\n{'=' * 60}\n## 📋 自我校验结果\n\n{check_result}"

    # ================================================================
    #  目录级评估 - 整个项目的深度分析
    # ================================================================

    def run_directory(self, directory: str, self_check: bool = False) -> str:
        """对整个目录进行扫描、分析与深度解读

        流程:
          1. 递归扫描目录，发现所有 Python 文件
          2. 逐文件 AST 解析 + Code Graph 构建
          3. 构建项目级依赖图（模块依赖、跨文件调用、类继承）
          4. 检测循环依赖、重名冲突、高复杂度热点
          5. LLM 对项目整体进行语义级深度解读
          6. 选取最值得关注的文件（≤5 个）进行单文件 LLM 评估
          7. 汇总问题清单与改进建议
          8. 更新长期记忆

        Args:
            directory:  项目根目录路径
            self_check: 是否在输出前附加自我校验

        Returns:
            Markdown 格式的项目级评估报告
        """
        import os
        logger.info("开始项目级评估: %s", directory)

        # 1. 目录扫描 + 逐文件分析
        scanner = DirectoryScanner()
        project = scanner.scan(directory)

        if project.total_files == 0:
            return "未发现 Python 文件。"

        # 2. LLM 深度解读
        deep_analysis = self._deep_interpret_project(project)

        # 3. 按文件汇总单文件评估（仅对较短文件做 LLM 评估，避免 token 爆炸）
        file_evaluations = self._evaluate_selected_files(project)

        # 4. 经验总结
        experience = self._summarize_project_experience(project, deep_analysis)

        # 5. 格式化项目级报告
        report = self.formatter.format_project(
            project=project,
            deep_analysis=deep_analysis,
            file_evaluations=file_evaluations,
            experience=experience,
        )

        if self_check:
            logger.info("执行自我校验...")
            check_result = self.self_check(report)
            report += f"\n\n{'=' * 60}\n## 📋 自我校验结果\n\n{check_result}"

        logger.info("项目级评估完成")
        return report

    def _deep_interpret_project(self, project: ProjectAnalysis) -> dict:
        """LLM 对项目整体进行语义级深度解读

        将项目的文件结构、依赖图、语法错误、循环依赖、各文件代码预览
        等信息组装为 prompt，由 LLM 输出 JSON 格式的全面架构评估。
        """
        logger.info("执行项目深度解读...")

        system_prompt = """\
你是一个高级软件架构分析专家。请对给定项目进行全面的语义级深度解读。

分析维度：
1. **项目概述**：项目的功能、用途、技术栈
2. **架构评估**：整体架构设计是否合理，模块划分是否清晰
3. **代码质量总览**：整体质量水平、一致性、规范性
4. **依赖关系分析**：模块间耦合度、是否存在不合理依赖
5. **安全性审查**：项目级安全风险
6. **可维护性评估**：扩展性、可测试性、文档完备度
7. **性能隐患**：潜在的性能瓶颈
8. **重构建议**：最值得改进的 Top-5 问题

请严格按以下 JSON 格式输出：
```json
{
  "project_summary": "一段话描述项目概况",
  "architecture": {
    "score": 0-10,
    "pattern": "识别出的架构模式",
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["弱点1", "弱点2"]
  },
  "code_quality": {
    "score": 0-10,
    "consistency": "代码一致性评价",
    "documentation": "文档完备度评价",
    "test_coverage_estimate": "测试覆盖估计"
  },
  "dependency_analysis": {
    "coupling_level": "低/中/高",
    "problematic_deps": ["问题依赖说明"],
    "suggestions": ["改进建议"]
  },
  "security_issues": [
    {"severity": "严重|中等|轻微", "description": "描述", "file": "相关文件"}
  ],
  "performance_concerns": ["性能隐患描述"],
  "top5_improvements": [
    {"priority": 1, "description": "改进描述", "impact": "预期效果", "effort": "低/中/高"}
  ],
  "overall_score": 0-10,
  "overall_comment": "总体评价"
}
```
"""
        # 构建项目上下文给 LLM
        ctx_parts = [f"项目路径: {project.root_dir}\n"]
        ctx_parts.append(f"文件数: {project.total_files}, 代码行: {project.total_code_lines}, "
                         f"函数: {project.total_functions}, 类: {project.total_classes}\n")

        if project.cross_file_graph:
            ctx_parts.append(f"项目结构与依赖图：\n{project.cross_file_graph}\n")

        if project.all_syntax_errors:
            ctx_parts.append("语法错误：")
            for se in project.all_syntax_errors:
                ctx_parts.append(f"  {se['file']}: {se['errors']}")
            ctx_parts.append("")

        if project.circular_deps:
            ctx_parts.append(f"循环依赖: {project.circular_deps}\n")

        if project.duplicate_names:
            ctx_parts.append("重名冲突：")
            for dn in project.duplicate_names:
                ctx_parts.append(f"  {dn['name']} 出现在: {dn['files']}")
            ctx_parts.append("")

        # 附上每个文件的关键代码摘要（截断以控制 token）
        ctx_parts.append("各文件概览：")
        for fa in project.files:
            ctx_parts.append(f"\n--- {fa.relative_path} ({fa.analysis.total_lines}行) ---")
            funcs = [f.name for f in fa.analysis.functions if not f.is_method]
            classes = [c.name for c in fa.analysis.classes]
            if classes:
                ctx_parts.append(f"  类: {classes}")
            if funcs:
                ctx_parts.append(f"  函数: {funcs}")
            # 附上文件头部（docstring/关键导入），限制长度
            preview = fa.source[:800]
            if len(fa.source) > 800:
                preview += "\n  ... (省略)"
            ctx_parts.append(f"  代码预览:\n{preview}")

        user_prompt = "\n".join(ctx_parts)
        return self.llm.chat_json(system_prompt, user_prompt)

    def _evaluate_selected_files(self, project: ProjectAnalysis) -> list[dict]:
        """对关键文件进行 LLM 评估

        选取策略：按 (最大圈复杂度×2 + 函数数 + 代码行/50) 降序，
        取 Top-5 最值得关注的文件逐一调用 Evaluator。
        """
        # 选取最多 5 个最值得关注的文件
        scored = []
        for fa in project.files:
            max_complexity = max(
                (f.complexity for f in fa.analysis.functions), default=1
            )
            score = max_complexity * 2 + len(fa.analysis.functions) + fa.analysis.code_lines / 50
            scored.append((score, fa))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [fa for _, fa in scored[:5]]

        results = []
        for fa in selected:
            logger.info("评估文件: %s", fa.relative_path)
            try:
                evaluation = self.evaluator.evaluate(fa.source, fa.analysis)
                results.append({
                    "file": fa.relative_path,
                    "evaluation": evaluation,
                    "lines": fa.analysis.total_lines,
                    "functions": len(fa.analysis.functions),
                    "classes": len(fa.analysis.classes),
                })
            except Exception as e:
                logger.warning("评估文件 %s 失败: %s", fa.relative_path, e)
                results.append({
                    "file": fa.relative_path,
                    "evaluation": {"overall_score": "N/A", "summary": f"评估失败: {e}"},
                    "lines": fa.analysis.total_lines,
                    "functions": len(fa.analysis.functions),
                    "classes": len(fa.analysis.classes),
                })

        return results

    def _summarize_project_experience(self, project: ProjectAnalysis, deep_analysis: dict) -> str:
        """项目级经验总结"""
        context = (
            f"项目规模: {project.total_files} 文件, {project.total_code_lines} 行代码\n"
            f"整体评分: {deep_analysis.get('overall_score', 'N/A')}/10\n"
        )
        arch = deep_analysis.get("architecture", {})
        if arch:
            context += f"架构评分: {arch.get('score', 'N/A')}/10\n"
            if arch.get("weaknesses"):
                context += f"架构弱点: {arch['weaknesses']}\n"

        top5 = deep_analysis.get("top5_improvements", [])
        if top5:
            context += "关键改进:\n"
            for item in top5[:3]:
                context += f"  - {item.get('description', '')}\n"

        user_prompt = f"请根据以下项目评估结果总结经验：\n{context}"
        result = self.llm.chat_json(EXPERIENCE_SYSTEM_PROMPT, user_prompt)

        entries = result.get("entries", [])
        for entry in entries:
            self.long_term_memory.add(
                category=entry.get("category", "general"),
                content=entry.get("content", ""),
                tags=entry.get("tags", []),
                source_file=project.root_dir,
            )
        return result.get("experience_text", "")
