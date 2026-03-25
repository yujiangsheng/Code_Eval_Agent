"""目录扫描器 — 递归扫描项目目录并构建跨文件的项目级分析

本模块实现从文件系统到项目级全景分析的完整管线:

  1. 递归文件发现（支持 ignore 列表过滤）
  2. 逐文件 AST 静态分析
  3. 跨文件关系分析:
     - 模块依赖图（基于 import 语句）
     - 循环依赖检测（DFS）
     - 跨文件函数/类重名检测
     - 跨文件调用追踪
     - 类继承关系映射
  4. 复杂度排行
  5. 项目级 Code Graph 生成
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from eval_agent.analyzer import CodeAnalyzer, AnalysisResult, FunctionInfo, ClassInfo, ImportInfo

logger = logging.getLogger(__name__)

# 默认忽略的目录
DEFAULT_IGNORE_DIRS = {
    "__pycache__", ".git", ".svn", ".hg", "node_modules",
    ".tox", ".eggs", "*.egg-info", "dist", "build",
    ".venv", "venv", "env", ".env", ".mypy_cache",
    ".pytest_cache", ".ruff_cache",
}

# 默认支持的文件后缀
DEFAULT_EXTENSIONS = {".py"}


@dataclass
class FileAnalysis:
    """单个文件的分析结果"""
    file_path: str
    relative_path: str
    source: str
    analysis: AnalysisResult
    size_bytes: int = 0


@dataclass
class ProjectAnalysis:
    """项目级分析总结果"""
    root_dir: str
    files: list[FileAnalysis] = field(default_factory=list)

    # 汇总指标
    total_files: int = 0
    total_lines: int = 0
    total_code_lines: int = 0
    total_comment_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_imports: int = 0

    # 跨文件关系
    cross_file_graph: str = ""
    module_dependencies: dict = field(default_factory=dict)  # module -> [imported_modules]
    all_syntax_errors: list[dict] = field(default_factory=list)  # [{file, errors}]

    # 项目级问题
    duplicate_names: list[dict] = field(default_factory=list)
    unused_imports: list[dict] = field(default_factory=list)
    circular_deps: list[list[str]] = field(default_factory=list)

    # 按复杂度排名
    complexity_ranking: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root_dir": self.root_dir,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_code_lines": self.total_code_lines,
            "total_comment_lines": self.total_comment_lines,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "total_imports": self.total_imports,
            "files": [
                {
                    "path": f.relative_path,
                    "lines": f.analysis.total_lines,
                    "code_lines": f.analysis.code_lines,
                    "functions": len(f.analysis.functions),
                    "classes": len(f.analysis.classes),
                    "syntax_errors": f.analysis.syntax_errors,
                }
                for f in self.files
            ],
            "syntax_errors": self.all_syntax_errors,
            "complexity_ranking": self.complexity_ranking[:20],
            "module_dependencies": self.module_dependencies,
            "circular_dependencies": self.circular_deps,
            "duplicate_names": self.duplicate_names,
        }


class DirectoryScanner:
    """目录扫描器 — 递归读取目录中所有 Python 文件并构建项目级分析

    扫描流程::

        scan(root_dir)
          ├─ 1. _discover_files()           递归发现 .py 文件
          ├─ 2. _analyze_file() × N         逐文件 AST 分析
          ├─ 3. _aggregate_metrics()         汇总行数/函数/类等指标
          ├─ 4. _analyze_cross_file()        跨文件依赖/重名/循环/复杂度
          └─ 5. _build_project_graph()       生成项目级 Code Graph 文本

    Attributes:
        extensions:    识别的文件后缀集合，默认 {'.py'}
        ignore_dirs:   跳过的目录名集合（__pycache__ 等）
        max_file_size: 跳过的单文件字节上限，默认 1 MB
        analyzer:      CodeAnalyzer 实例
    """

    def __init__(
        self,
        extensions: Optional[set[str]] = None,
        ignore_dirs: Optional[set[str]] = None,
        max_file_size: int = 1024 * 1024,  # 1MB
    ):
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS
        self.max_file_size = max_file_size
        self.analyzer = CodeAnalyzer()

    def scan(self, root_dir: str) -> ProjectAnalysis:
        """扫描目录，对所有 Python 文件进行分析

        Args:
            root_dir: 项目根目录路径

        Returns:
            ProjectAnalysis 项目级分析结果
        """
        root_dir = os.path.abspath(root_dir)
        if not os.path.isdir(root_dir):
            raise ValueError(f"不是有效目录: {root_dir}")

        project = ProjectAnalysis(root_dir=root_dir)

        # 1. 递归发现所有文件
        py_files = self._discover_files(root_dir)
        logger.info("发现 %d 个 Python 文件", len(py_files))

        # 2. 逐文件分析
        for filepath in sorted(py_files):
            fa = self._analyze_file(filepath, root_dir)
            if fa:
                project.files.append(fa)

        project.total_files = len(project.files)

        # 3. 汇总指标
        self._aggregate_metrics(project)

        # 4. 跨文件分析
        self._analyze_cross_file(project)

        # 5. 构建项目级 Code Graph
        project.cross_file_graph = self._build_project_graph(project)

        logger.info(
            "项目分析完成: %d 文件, %d 行代码, %d 函数, %d 类",
            project.total_files,
            project.total_code_lines,
            project.total_functions,
            project.total_classes,
        )
        return project

    def _discover_files(self, root_dir: str) -> list[str]:
        """递归发现目标文件"""
        files = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # 过滤忽略目录
            dirnames[:] = [
                d for d in dirnames
                if d not in self.ignore_dirs
                and not any(d.endswith(pat.lstrip("*")) for pat in self.ignore_dirs if "*" in pat)
            ]
            for fname in filenames:
                ext = os.path.splitext(fname)[1]
                if ext in self.extensions:
                    full_path = os.path.join(dirpath, fname)
                    files.append(full_path)
        return files

    def _analyze_file(self, filepath: str, root_dir: str) -> Optional[FileAnalysis]:
        """分析单个文件"""
        try:
            size = os.path.getsize(filepath)
            if size > self.max_file_size:
                logger.warning("跳过过大文件: %s (%d bytes)", filepath, size)
                return None
            if size == 0:
                return None

            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()

            rel_path = os.path.relpath(filepath, root_dir)
            analysis = self.analyzer.analyze(source, filename=rel_path)

            return FileAnalysis(
                file_path=filepath,
                relative_path=rel_path,
                source=source,
                analysis=analysis,
                size_bytes=size,
            )
        except Exception as e:
            logger.warning("分析文件失败 %s: %s", filepath, e)
            return None

    def _aggregate_metrics(self, project: ProjectAnalysis):
        """汇总所有文件的指标"""
        for fa in project.files:
            a = fa.analysis
            project.total_lines += a.total_lines
            project.total_code_lines += a.code_lines
            project.total_comment_lines += a.comment_lines
            project.total_functions += len(a.functions)
            project.total_classes += len(a.classes)
            project.total_imports += len(a.imports)

            if a.syntax_errors:
                project.all_syntax_errors.append({
                    "file": fa.relative_path,
                    "errors": a.syntax_errors,
                })

    def _analyze_cross_file(self, project: ProjectAnalysis):
        """跨文件分析：模块依赖、循环依赖检测、重名检测、复杂度排名

        分析策略：
        - 依赖图：将文件路径转为模块名，匹配 import 语句中的本地模块
        - 循环依赖：在依赖图上执行 DFS，记录 back-edge 形成的环路
        - 重名检测：仅检测顶层函数和类，方法不计入
        - 复杂度排名：按 McCabe 圈复杂度降序排列所有函数
        """

        # --- 模块依赖分析 ---
        # 收集所有本项目的模块名
        local_modules = set()
        for fa in project.files:
            # 将文件路径转为模块名: a/b/c.py -> a.b.c
            mod = fa.relative_path.replace(os.sep, ".").removesuffix(".py")
            if mod.endswith(".__init__"):
                mod = mod.removesuffix(".__init__")
            local_modules.add(mod)

        for fa in project.files:
            mod_name = fa.relative_path.replace(os.sep, ".").removesuffix(".py")
            if mod_name.endswith(".__init__"):
                mod_name = mod_name.removesuffix(".__init__")
            deps = []
            for imp in fa.analysis.imports:
                m = imp.module
                if m in local_modules or any(m.startswith(lm + ".") for lm in local_modules):
                    deps.append(m)
            if deps:
                project.module_dependencies[mod_name] = deps

        # --- 循环依赖检测 ---
        project.circular_deps = self._detect_cycles(project.module_dependencies)

        # --- 函数/类重名检测 ---
        name_locations: dict[str, list[str]] = {}
        for fa in project.files:
            for func in fa.analysis.functions:
                if func.is_method:
                    continue  # 方法不检测跨文件重名
                key = f"函数 {func.name}"
                name_locations.setdefault(key, []).append(fa.relative_path)
            for cls in fa.analysis.classes:
                key = f"类 {cls.name}"
                name_locations.setdefault(key, []).append(fa.relative_path)

        for name, locations in name_locations.items():
            if len(locations) > 1:
                project.duplicate_names.append({
                    "name": name,
                    "files": locations,
                })

        # --- 复杂度排名 ---
        all_funcs = []
        for fa in project.files:
            for func in fa.analysis.functions:
                full_name = f"{func.class_name}.{func.name}" if func.class_name else func.name
                all_funcs.append({
                    "name": full_name,
                    "file": fa.relative_path,
                    "line": func.lineno,
                    "complexity": func.complexity,
                })
        all_funcs.sort(key=lambda x: x["complexity"], reverse=True)
        project.complexity_ranking = all_funcs

    def _detect_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """检测有向图中的循环（简易 DFS）"""
        visited = set()
        on_stack = set()
        cycles = []

        def dfs(node: str, path: list[str]):
            visited.add(node)
            on_stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in on_stack:
                    # 找到循环
                    idx = path.index(neighbor) if neighbor in path else -1
                    if idx >= 0:
                        cycle = path[idx:] + [neighbor]
                        cycles.append(cycle)
            path.pop()
            on_stack.discard(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _build_project_graph(self, project: ProjectAnalysis) -> str:
        """构建项目级 Code Graph 文本

        包含五个段落::

            [项目结构]       每个文件及其类/函数/方法数量
            [模块依赖]       模块间 import 关系
            [⚠️ 循环依赖]    检测到的循环
            [跨文件调用]     函数 A（文件X）→ 函数 B（文件Y）
            [类继承]         跨文件或同文件的继承关系
            [🔥 高复杂度热点] 圈复杂度 > 10 的函数
        """
        lines = []

        # --- 文件结构概览 ---
        lines.append("[项目结构]")
        for fa in project.files:
            n_func = len([f for f in fa.analysis.functions if not f.is_method])
            n_cls = len(fa.analysis.classes)
            n_method = len([f for f in fa.analysis.functions if f.is_method])
            parts = []
            if n_cls:
                parts.append(f"{n_cls}类")
            if n_func:
                parts.append(f"{n_func}函数")
            if n_method:
                parts.append(f"{n_method}方法")
            desc = ", ".join(parts) if parts else "空"
            lines.append(f"  📄 {fa.relative_path}  ({desc})")

        # --- 模块依赖关系 ---
        if project.module_dependencies:
            lines.append("")
            lines.append("[模块依赖]")
            for mod, deps in sorted(project.module_dependencies.items()):
                for dep in deps:
                    lines.append(f"  {mod} -> {dep}")

        # --- 循环依赖 ---
        if project.circular_deps:
            lines.append("")
            lines.append("[⚠️ 循环依赖]")
            for cycle in project.circular_deps:
                lines.append(f"  {' -> '.join(cycle)}")

        # --- 跨文件调用（最重要的函数互调关系）---
        # 收集所有顶层定义
        defined_in: dict[str, str] = {}  # name -> file
        for fa in project.files:
            for func in fa.analysis.functions:
                if not func.is_method:
                    defined_in[func.name] = fa.relative_path
            for cls in fa.analysis.classes:
                defined_in[cls.name] = fa.relative_path

        cross_calls = []
        for fa in project.files:
            for func in fa.analysis.functions:
                for callee in func.calls:
                    if callee in defined_in and defined_in[callee] != fa.relative_path:
                        caller_name = f"{func.class_name}.{func.name}" if func.class_name else func.name
                        cross_calls.append(
                            (fa.relative_path, caller_name, defined_in[callee], callee)
                        )

        if cross_calls:
            lines.append("")
            lines.append("[跨文件调用]")
            for src_file, caller, dst_file, callee in cross_calls:
                lines.append(f"  {src_file}::{caller} -> {dst_file}::{callee}")

        # --- 类继承关系（跨文件）---
        class_file: dict[str, str] = {}
        for fa in project.files:
            for cls in fa.analysis.classes:
                class_file[cls.name] = fa.relative_path

        inheritance = []
        for fa in project.files:
            for cls in fa.analysis.classes:
                for base in cls.bases:
                    if base in class_file:
                        inheritance.append((cls.name, base, fa.relative_path, class_file[base]))

        if inheritance:
            lines.append("")
            lines.append("[类继承]")
            for child, parent, child_file, parent_file in inheritance:
                if child_file == parent_file:
                    lines.append(f"  {child} -> {parent}  (同文件: {child_file})")
                else:
                    lines.append(f"  {child}({child_file}) -> {parent}({parent_file})")

        # --- 高复杂度热点 ---
        hot = [f for f in project.complexity_ranking if f["complexity"] > 10]
        if hot:
            lines.append("")
            lines.append("[🔥 高复杂度热点]")
            for f in hot[:10]:
                lines.append(f"  {f['file']}::{f['name']}  复杂度={f['complexity']}")

        return "\n".join(lines)
