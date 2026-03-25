"""输出格式化器 — 将评估结果转换为结构化 Markdown 报告

本模块负责最终输出的呈现，支持两种报告模式:

  1. **单文件报告** ``format()`` — 8 个章节
     ① 总体评估  ② 问题清单  ③ 代码结构分析  ④ 修复方案
     ⑤ 优化后代码  ⑥ 关键改进说明  ⑦ 测试用例  ⑧ 经验总结

  2. **项目级报告** ``format_project()`` — 9 个章节
     ① 项目总览  ② 架构评估  ③ 项目结构 & Code Graph
     ④ 依赖关系分析  ⑤ 问题清单  ⑥ 关键文件评估
     ⑦ 复杂度排行  ⑧ Top-5 改进建议  ⑨ 经验总结
"""

from __future__ import annotations

from typing import Optional

from eval_agent.analyzer import AnalysisResult
from eval_agent.scanner import ProjectAnalysis


class OutputFormatter:
    """Eval Agent 输出格式化器

    将评估流水线各阶段的结构化数据转换为人类可读的 Markdown 报告。
    支持单文件（8 章节）和项目级（9 章节）两种报告格式。
    """

    SEPARATOR = "=" * 60

    def format(
        self,
        evaluation: dict,
        analysis: AnalysisResult,
        fix_result: Optional[dict],
        improve_result: Optional[dict],
        test_result: Optional[dict],
        experience: str = "",
    ) -> str:
        """格式化完整输出"""
        sections = [
            self._header(),
            self._section_evaluation(evaluation),
            self._section_issues(evaluation.get("issues", [])),
            self._section_structure(analysis),
            self._section_fixes(fix_result),
            self._section_improved_code(improve_result),
            self._section_improvements(improve_result),
            self._section_tests(test_result),
            self._section_experience(experience),
        ]
        return "\n\n".join(s for s in sections if s)

    def _header(self) -> str:
        return f"{self.SEPARATOR}\n  Eval Agent - 代码评估与进化报告\n{self.SEPARATOR}"

    # ---- 1. 总体评估 ----
    def _section_evaluation(self, evaluation: dict) -> str:
        lines = ["## 1. 总体评估\n"]
        score = evaluation.get("overall_score", "N/A")
        summary = evaluation.get("summary", "")
        lines.append(f"**总分：{score} / 10**\n")
        if summary:
            lines.append(f"{summary}\n")

        dims = evaluation.get("dimensions", {})
        if dims:
            lines.append("| 维度 | 得分 | 说明 |")
            lines.append("|------|------|------|")
            dim_names = {
                "syntax": "语法正确性",
                "logic": "逻辑正确性",
                "boundary": "边界条件",
                "complexity": "时间/空间复杂度",
                "security": "安全性",
                "style": "代码规范",
                "maintainability": "可维护性",
            }
            for key, info in dims.items():
                name = dim_names.get(key, key)
                s = info.get("score", "N/A")
                c = info.get("comment", "")
                extra = ""
                if key == "complexity":
                    t = info.get("time", "")
                    sp = info.get("space", "")
                    if t or sp:
                        extra = f" (时间: {t}, 空间: {sp})"
                lines.append(f"| {name} | {s}/10 | {c}{extra} |")
        return "\n".join(lines)

    # ---- 2. 问题清单 ----
    def _section_issues(self, issues: list[dict]) -> str:
        if not issues:
            return "## 2. 问题清单\n\n✅ 未发现问题"

        lines = ["## 2. 问题清单\n"]

        for severity in ["严重", "中等", "轻微"]:
            group = [i for i in issues if i.get("severity") == severity]
            if not group:
                continue
            icon = {"严重": "🔴", "中等": "🟡", "轻微": "🔵"}.get(severity, "⚪")
            lines.append(f"### {icon} {severity}")
            for i, issue in enumerate(group, 1):
                itype = issue.get("type", "")
                line = issue.get("line")
                desc = issue.get("description", "")
                suggestion = issue.get("suggestion", "")
                loc = f" (行 {line})" if line else ""
                lines.append(f"{i}. **[{itype}]{loc}** {desc}")
                if suggestion:
                    lines.append(f"   → 建议：{suggestion}")
            lines.append("")

        return "\n".join(lines)

    # ---- 3. 代码结构分析 ----
    def _section_structure(self, analysis: AnalysisResult) -> str:
        lines = ["## 3. 代码结构分析\n"]
        info = analysis.to_dict()
        m = info["metrics"]
        lines.append(f"- 总行数：{m['total_lines']}")
        lines.append(f"- 有效代码行：{m['code_lines']}")
        lines.append(f"- 注释行：{m['comment_lines']}")
        lines.append(f"- 函数数量：{len(info['functions'])}")
        lines.append(f"- 类数量：{len(info['classes'])}")
        lines.append(f"- 导入数量：{len(info['imports'])}")

        if analysis.code_graph:
            lines.append(f"\n### Code Graph\n```\n{analysis.code_graph}\n```")

        return "\n".join(lines)

    # ---- 4. 修复与改进方案 ----
    def _section_fixes(self, fix_result: Optional[dict]) -> str:
        if not fix_result:
            return ""
        lines = ["## 4. 修复方案\n"]
        fixes = fix_result.get("fixes", [])
        if fixes:
            for i, fix in enumerate(fixes, 1):
                desc = fix.get("description", "")
                reason = fix.get("reason", "")
                lines.append(f"{i}. **{desc}**")
                if reason:
                    lines.append(f"   原因：{reason}")
        notes = fix_result.get("notes", "")
        if notes:
            lines.append(f"\n⚠️ 备注：{notes}")
        confidence = fix_result.get("confidence")
        if confidence is not None:
            lines.append(f"\n修复信心：{confidence}/10")
        return "\n".join(lines)

    # ---- 5. 优化后代码 ----
    def _section_improved_code(self, improve_result: Optional[dict]) -> str:
        if not improve_result:
            return ""
        code = improve_result.get("improved_code", "")
        if not code:
            return ""
        return f"## 5. 优化后代码\n\n```python\n{code}\n```"

    # ---- 6. 关键改进说明 ----
    def _section_improvements(self, improve_result: Optional[dict]) -> str:
        if not improve_result:
            return ""
        improvements = improve_result.get("improvements", [])
        if not improvements:
            return ""
        lines = ["## 6. 关键改进说明\n"]
        type_icons = {
            "refactor": "🔄",
            "performance": "⚡",
            "structure": "🏗️",
            "readability": "📖",
        }
        for i, imp in enumerate(improvements, 1):
            itype = imp.get("type", "")
            icon = type_icons.get(itype, "✨")
            desc = imp.get("description", "")
            impact = imp.get("impact", "")
            lines.append(f"{i}. {icon} **{desc}**")
            if impact:
                lines.append(f"   效果：{impact}")

        summary = improve_result.get("before_after_summary", "")
        if summary:
            lines.append(f"\n**改进总结**：{summary}")

        return "\n".join(lines)

    # ---- 7. 测试用例 ----
    def _section_tests(self, test_result: Optional[dict]) -> str:
        if not test_result:
            return ""
        lines = ["## 7. 测试用例\n"]
        test_cases = test_result.get("test_cases", [])
        if test_cases:
            cat_icons = {
                "normal": "✅",
                "boundary": "🔲",
                "exception": "❌",
                "performance": "⏱️",
            }
            for tc in test_cases:
                cat = tc.get("category", "")
                icon = cat_icons.get(cat, "🔹")
                lines.append(f"- {icon} `{tc.get('name', '')}`: {tc.get('description', '')}")

        code = test_result.get("test_code", "")
        if code:
            lines.append(f"\n```python\n{code}\n```")

        notes = test_result.get("coverage_notes", "")
        if notes:
            lines.append(f"\n📋 覆盖说明：{notes}")

        return "\n".join(lines)

    # ---- 8. 经验总结 ----
    def _section_experience(self, experience: str) -> str:
        if not experience:
            return ""
        return f"## 8. 经验总结\n\n{experience}"

    # ================================================================
    #  项目级报告格式化
    # ================================================================

    def format_project(
        self,
        project: ProjectAnalysis,
        deep_analysis: dict,
        file_evaluations: list[dict],
        experience: str = "",
    ) -> str:
        """格式化项目级评估报告"""
        sections = [
            self._proj_header(project),
            self._proj_overview(project, deep_analysis),
            self._proj_architecture(deep_analysis),
            self._proj_structure(project),
            self._proj_dependency(project, deep_analysis),
            self._proj_issues(project, deep_analysis),
            self._proj_file_evaluations(file_evaluations),
            self._proj_complexity(project),
            self._proj_improvements(deep_analysis),
            self._proj_experience(experience),
        ]
        return "\n\n".join(s for s in sections if s)

    def _proj_header(self, project: ProjectAnalysis) -> str:
        return (
            f"{self.SEPARATOR}\n"
            f"  Eval Agent - 项目级深度分析报告\n"
            f"  {project.root_dir}\n"
            f"{self.SEPARATOR}"
        )

    def _proj_overview(self, project: ProjectAnalysis, deep_analysis: dict) -> str:
        lines = ["## 1. 项目总览\n"]
        score = deep_analysis.get("overall_score", "N/A")
        comment = deep_analysis.get("overall_comment", "")
        summary = deep_analysis.get("project_summary", "")
        lines.append(f"**总体评分：{score} / 10**\n")
        if summary:
            lines.append(f"{summary}\n")
        if comment:
            lines.append(f"_{comment}_\n")

        lines.append("### 项目规模")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 文件数 | {project.total_files} |")
        lines.append(f"| 总行数 | {project.total_lines} |")
        lines.append(f"| 有效代码行 | {project.total_code_lines} |")
        lines.append(f"| 注释行 | {project.total_comment_lines} |")
        lines.append(f"| 函数总数 | {project.total_functions} |")
        lines.append(f"| 类总数 | {project.total_classes} |")
        lines.append(f"| 导入总数 | {project.total_imports} |")

        if project.total_code_lines > 0:
            comment_ratio = project.total_comment_lines / project.total_code_lines * 100
            lines.append(f"| 注释率 | {comment_ratio:.1f}% |")

        return "\n".join(lines)

    def _proj_architecture(self, deep_analysis: dict) -> str:
        arch = deep_analysis.get("architecture", {})
        if not arch:
            return ""

        lines = ["## 2. 架构评估\n"]
        score = arch.get("score", "N/A")
        pattern = arch.get("pattern", "未识别")
        lines.append(f"**架构评分：{score} / 10**  |  架构模式：{pattern}\n")

        strengths = arch.get("strengths", [])
        if strengths:
            lines.append("### ✅ 优势")
            for s in strengths:
                lines.append(f"- {s}")

        weaknesses = arch.get("weaknesses", [])
        if weaknesses:
            lines.append("\n### ⚠️ 弱点")
            for w in weaknesses:
                lines.append(f"- {w}")

        return "\n".join(lines)

    def _proj_structure(self, project: ProjectAnalysis) -> str:
        lines = ["## 3. 项目结构与 Code Graph\n"]
        if project.cross_file_graph:
            lines.append(f"```\n{project.cross_file_graph}\n```")
        else:
            lines.append("（项目结构较简单）")
        return "\n".join(lines)

    def _proj_dependency(self, project: ProjectAnalysis, deep_analysis: dict) -> str:
        lines = ["## 4. 依赖关系分析\n"]

        dep = deep_analysis.get("dependency_analysis", {})
        if dep:
            coupling = dep.get("coupling_level", "未知")
            lines.append(f"**耦合度：{coupling}**\n")
            problems = dep.get("problematic_deps", [])
            if problems:
                lines.append("### 问题依赖")
                for p in problems:
                    lines.append(f"- 🔴 {p}")
            suggestions = dep.get("suggestions", [])
            if suggestions:
                lines.append("\n### 改进建议")
                for s in suggestions:
                    lines.append(f"- 💡 {s}")

        if project.module_dependencies:
            lines.append("\n### 模块依赖图")
            for mod, deps in sorted(project.module_dependencies.items()):
                lines.append(f"- `{mod}` → {', '.join(f'`{d}`' for d in deps)}")

        if project.circular_deps:
            lines.append("\n### ⚠️ 循环依赖")
            for cycle in project.circular_deps:
                lines.append(f"- 🔴 {' → '.join(cycle)}")

        return "\n".join(lines)

    def _proj_issues(self, project: ProjectAnalysis, deep_analysis: dict) -> str:
        lines = ["## 5. 问题清单\n"]
        has_issues = False

        # 语法错误
        if project.all_syntax_errors:
            has_issues = True
            lines.append("### 🔴 语法错误")
            for se in project.all_syntax_errors:
                lines.append(f"- `{se['file']}`: {', '.join(se['errors'])}")

        # 重名冲突
        if project.duplicate_names:
            has_issues = True
            lines.append("\n### 🟡 名称冲突")
            for dn in project.duplicate_names:
                files = ", ".join(f"`{f}`" for f in dn["files"])
                lines.append(f"- {dn['name']} 重复定义于: {files}")

        # 安全问题
        security = deep_analysis.get("security_issues", [])
        if security:
            has_issues = True
            lines.append("\n### 🔐 安全问题")
            sev_icons = {"严重": "🔴", "中等": "🟡", "轻微": "🔵"}
            for si in security:
                sev = si.get("severity", "轻微")
                icon = sev_icons.get(sev, "⚪")
                desc = si.get("description", "")
                f = si.get("file", "")
                loc = f" (`{f}`)" if f else ""
                lines.append(f"- {icon} [{sev}]{loc} {desc}")

        # 性能隐患
        perf = deep_analysis.get("performance_concerns", [])
        if perf:
            has_issues = True
            lines.append("\n### ⚡ 性能隐患")
            for p in perf:
                lines.append(f"- {p}")

        if not has_issues:
            lines.append("✅ 未发现严重问题")

        return "\n".join(lines)

    def _proj_file_evaluations(self, file_evaluations: list[dict]) -> str:
        if not file_evaluations:
            return ""
        lines = ["## 6. 关键文件评估\n"]
        lines.append("| 文件 | 行数 | 函数 | 类 | 评分 | 说明 |")
        lines.append("|------|------|------|-----|------|------|")
        for fe in file_evaluations:
            ev = fe.get("evaluation", {})
            score = ev.get("overall_score", "N/A")
            summary = ev.get("summary", "")[:60]
            lines.append(
                f"| `{fe['file']}` | {fe['lines']} | {fe['functions']} "
                f"| {fe['classes']} | {score}/10 | {summary} |"
            )

        # 详细的单文件问题
        for fe in file_evaluations:
            ev = fe.get("evaluation", {})
            issues = ev.get("issues", [])
            if issues:
                lines.append(f"\n### 📄 {fe['file']}")
                for i, issue in enumerate(issues, 1):
                    sev = issue.get("severity", "")
                    desc = issue.get("description", "")
                    lines.append(f"  {i}. [{sev}] {desc}")

        return "\n".join(lines)

    def _proj_complexity(self, project: ProjectAnalysis) -> str:
        ranking = project.complexity_ranking
        if not ranking:
            return ""
        lines = ["## 7. 复杂度排行\n"]
        lines.append("| 排名 | 函数 | 文件 | 行号 | 圈复杂度 |")
        lines.append("|------|------|------|------|----------|")
        for i, item in enumerate(ranking[:15], 1):
            c = item["complexity"]
            icon = "🔴" if c > 15 else "🟡" if c > 10 else "🔵" if c > 5 else ""
            lines.append(
                f"| {i} | `{item['name']}` | `{item['file']}` "
                f"| {item['line']} | {icon} {c} |"
            )
        return "\n".join(lines)

    def _proj_improvements(self, deep_analysis: dict) -> str:
        top5 = deep_analysis.get("top5_improvements", [])
        if not top5:
            return ""
        lines = ["## 8. Top-5 改进建议\n"]
        effort_icons = {"低": "🟢", "中": "🟡", "高": "🔴"}
        for item in top5:
            pri = item.get("priority", "?")
            desc = item.get("description", "")
            impact = item.get("impact", "")
            effort = item.get("effort", "")
            eicon = effort_icons.get(effort, "⚪")
            lines.append(f"### {pri}. {desc}")
            lines.append(f"- 预期效果：{impact}")
            lines.append(f"- 投入成本：{eicon} {effort}")
            lines.append("")
        return "\n".join(lines)

    def _proj_experience(self, experience: str) -> str:
        if not experience:
            return ""
        return f"## 9. 经验总结\n\n{experience}"
