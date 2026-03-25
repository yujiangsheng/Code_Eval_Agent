"""代码分析器 — 多语言静态分析与 Code Graph 构建

本模块是 Eval Agent 的核心分析引擎，支持多种编程语言：

  - **Python**: 基于 ``ast`` 模块的深度分析（函数、类、导入、圈复杂度）
  - **其他语言**: 基于正则的通用分析（函数、类、导入提取）

功能：
  1. **源码解析**：提取函数、类、导入、全局变量
  2. **圈复杂度**：使用 McCabe 方法（Python）或近似估算（其他语言）
  3. **Code Graph**：以文本形式描述代码的类结构、函数列表、调用关系和复杂度热点
  4. **语言检测**：根据文件后缀自动识别编程语言

数据结构层次::

    AnalysisResult
    ├── functions: list[FunctionInfo]   # 所有函数（含方法）
    ├── classes:   list[ClassInfo]      # 所有类
    ├── imports:   list[ImportInfo]     # 所有导入
    ├── global_variables: list[str]     # 模块级变量名
    ├── metrics:  total_lines / code_lines / comment_lines
    └── code_graph: str                 # 文本形式的 Code Graph
"""

from __future__ import annotations

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================
#  语言检测与配置
# ============================================================

# 文件后缀 -> (语言名, 代码块语言标识, 注释符号, 编码规范, 测试框架)
LANGUAGE_MAP = {
    ".py":    ("Python",      "python",     "#",   "PEP 8",        "pytest"),
    ".js":    ("JavaScript",  "javascript", "//",  "ESLint/Airbnb", "Jest"),
    ".ts":    ("TypeScript",  "typescript", "//",  "ESLint/TS",    "Jest"),
    ".jsx":   ("JavaScript (JSX)", "jsx",    "//",  "ESLint/Airbnb", "Jest"),
    ".tsx":   ("TypeScript (TSX)", "tsx",     "//",  "ESLint/TS",    "Jest"),
    ".java":  ("Java",        "java",       "//",  "Google Java Style", "JUnit"),
    ".c":     ("C",           "c",          "//",  "C99/C11 规范",   "Unity/CUnit"),
    ".cpp":   ("C++",         "cpp",        "//",  "C++ Core Guidelines", "Google Test"),
    ".h":     ("C/C++ Header","c",          "//",  "C/C++ 规范",     ""),
    ".hpp":   ("C++ Header",  "cpp",        "//",  "C++ Core Guidelines", ""),
    ".go":    ("Go",          "go",         "//",  "Effective Go",  "go test"),
    ".rs":    ("Rust",        "rust",       "//",  "Rust API Guidelines", "cargo test"),
    ".rb":    ("Ruby",        "ruby",       "#",   "RuboCop",       "RSpec"),
    ".php":   ("PHP",         "php",        "//",  "PSR-12",        "PHPUnit"),
    ".cs":    ("C#",          "csharp",     "//",  ".NET 编码规范",  "xUnit/NUnit"),
    ".swift": ("Swift",       "swift",      "//",  "Swift API Design Guidelines", "XCTest"),
    ".kt":    ("Kotlin",      "kotlin",     "//",  "Kotlin Coding Conventions", "JUnit/KotlinTest"),
    ".kts":   ("Kotlin Script","kotlin",    "//",  "Kotlin Coding Conventions", "JUnit/KotlinTest"),
    ".scala": ("Scala",       "scala",      "//",  "Scala Style Guide", "ScalaTest"),
    ".lua":   ("Lua",         "lua",        "--",  "Lua Style Guide", "busted"),
    ".sh":    ("Shell",       "bash",       "#",   "ShellCheck",    "bats"),
    ".bash":  ("Bash",        "bash",       "#",   "ShellCheck",    "bats"),
    ".r":     ("R",           "r",          "#",   "tidyverse style guide", "testthat"),
    ".R":     ("R",           "r",          "#",   "tidyverse style guide", "testthat"),
    ".m":     ("Objective-C", "objectivec", "//",  "Apple Coding Guidelines", "XCTest"),
}


def detect_language(filename: str) -> tuple[str, str, str, str, str]:
    """根据文件名检测编程语言

    Returns:
        (语言名, 代码块标识, 注释符号, 编码规范, 测试框架)
    """
    ext = os.path.splitext(filename)[1].lower() if filename else ""
    return LANGUAGE_MAP.get(ext, ("未知", "", "//", "通用编码规范", ""))


# ============================================================
#  数据结构定义
# ============================================================

@dataclass
class FunctionInfo:
    """函数 / 方法的元信息

    Attributes:
        name:        函数名
        lineno:      定义起始行号
        end_lineno:  定义结束行号（Python 3.8+）
        args:        参数名列表
        decorators:  装饰器名列表
        calls:       函数体内调用的其他函数名（去重）
        complexity:  McCabe 圈复杂度
        docstring:   文档字符串（首行）
        is_method:   是否为类方法
        class_name:  所属类名（若为方法）
    """
    name: str
    lineno: int
    end_lineno: Optional[int]
    args: list[str]
    decorators: list[str]
    calls: list[str]
    complexity: int = 1
    docstring: Optional[str] = None
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class ClassInfo:
    """类的元信息"""
    name: str
    lineno: int
    end_lineno: Optional[int]
    bases: list[str]
    methods: list[str]
    decorators: list[str]
    docstring: Optional[str] = None


@dataclass
class ImportInfo:
    """导入语句的元信息"""
    module: str
    names: list[str]
    lineno: int
    is_from: bool = False


@dataclass
class AnalysisResult:
    """单个文件的静态分析完整结果

    包含代码结构信息、行数指标和文本 Code Graph。
    """
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    global_variables: list[str] = field(default_factory=list)
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    syntax_errors: list[str] = field(default_factory=list)
    code_graph: str = ""
    language: str = "Python"
    lang_id: str = "python"

    def to_dict(self) -> dict:
        """将分析结果序列化为可 JSON 化的字典"""
        return {
            "functions": [
                {
                    "name": f.name,
                    "lineno": f.lineno,
                    "args": f.args,
                    "calls": f.calls,
                    "complexity": f.complexity,
                    "has_docstring": f.docstring is not None,
                    "class": f.class_name,
                }
                for f in self.functions
            ],
            "classes": [
                {
                    "name": c.name,
                    "lineno": c.lineno,
                    "bases": c.bases,
                    "methods": c.methods,
                    "has_docstring": c.docstring is not None,
                }
                for c in self.classes
            ],
            "imports": [
                {"module": i.module, "names": i.names, "is_from": i.is_from}
                for i in self.imports
            ],
            "global_variables": self.global_variables,
            "metrics": {
                "total_lines": self.total_lines,
                "code_lines": self.code_lines,
                "comment_lines": self.comment_lines,
            },
            "syntax_errors": self.syntax_errors,
            "language": self.language,
            "lang_id": self.lang_id,
        }


# ============================================================
#  分析器主体
# ============================================================

class CodeAnalyzer:
    """多语言代码静态分析器

    分析流程::

        source → 语言检测 → 行数统计 → 结构提取 → 构建 Code Graph

    - Python: 使用 ast 模块进行深度 AST 分析
    - 其他语言: 使用正则表达式进行通用结构提取
    """

    def analyze(self, source: str, filename: str = "<input>") -> AnalysisResult:
        """分析一段源代码

        Args:
            source:   完整的源码字符串
            filename: 文件名（用于语言检测和错误提示）

        Returns:
            AnalysisResult 包含函数、类、导入等全部静态信息
        """
        lang_name, lang_id, comment_char, _, _ = detect_language(filename)
        result = AnalysisResult()
        result.language = lang_name
        result.lang_id = lang_id
        result.total_lines = len(source.splitlines())

        if lang_name == "Python":
            return self._analyze_python(source, filename, result)
        else:
            return self._analyze_generic(source, filename, result, comment_char)

    # ============================================================
    #  Python 专用分析（基于 AST）
    # ============================================================

    def _analyze_python(self, source: str, filename: str, result: AnalysisResult) -> AnalysisResult:
        """使用 ast 模块对 Python 源码进行深度分析"""

        # 统计行类型
        self._count_lines(source, result, "#")

        # 尝试 AST 解析
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as e:
            result.syntax_errors.append(f"语法错误 (行 {e.lineno}): {e.msg}")
            return result

        # 提取信息
        self._extract_imports(tree, result)
        self._extract_classes(tree, result)
        self._extract_functions(tree, result)
        self._extract_globals(tree, result)

        # 构建 Code Graph
        result.code_graph = self._build_code_graph(result)

        return result

    # ============================================================
    #  通用语言分析（基于正则）
    # ============================================================

    # 各语言的函数/类/导入正则模式
    _GENERIC_PATTERNS = {
        "function": {
            "JavaScript":  r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[^=])\s*=>)',
            "TypeScript":  r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*(?::[^=]*)?\s*=\s*(?:async\s*)?(?:\([^)]*\)|[^=])\s*=>)',
            "Java":        r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{',
            "C":           r'(?:static\s+|extern\s+|inline\s+)*\w[\w\s*]+\s+(\w+)\s*\([^)]*\)\s*\{',
            "C++":         r'(?:static\s+|virtual\s+|inline\s+|explicit\s+)*[\w:<>\s*&]+\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\s*(?:override\s*)?\{',
            "Go":          r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(',
            "Rust":        r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)',
            "Ruby":        r'def\s+(\w+[?!]?)',
            "PHP":         r'(?:public|private|protected|static|\s)*function\s+(\w+)',
            "C#":          r'(?:public|private|protected|internal|static|virtual|override|async|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)',
            "Swift":       r'(?:public\s+|private\s+|internal\s+|open\s+)?func\s+(\w+)',
            "Kotlin":      r'(?:public\s+|private\s+|internal\s+|protected\s+)?fun\s+(?:<[^>]+>\s+)?(\w+)',
            "Scala":       r'def\s+(\w+)',
            "Lua":         r'(?:local\s+)?function\s+(\w+(?:\.\w+)*)',
            "Shell":       r'(?:function\s+(\w+)|(\w+)\s*\(\s*\))',
            "Bash":        r'(?:function\s+(\w+)|(\w+)\s*\(\s*\))',
            "R":           r'(\w+)\s*<-\s*function',
            "Objective-C": r'[-+]\s*\([^)]*\)\s*(\w+)',
        },
        "class": {
            "JavaScript":  r'class\s+(\w+)',
            "TypeScript":  r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)',
            "Java":        r'(?:public|private|protected|abstract|\s)*class\s+(\w+)',
            "C++":         r'(?:class|struct)\s+(\w+)',
            "Go":          r'type\s+(\w+)\s+struct',
            "Rust":        r'(?:pub\s+)?(?:struct|enum|trait)\s+(\w+)',
            "Ruby":        r'class\s+(\w+)',
            "PHP":         r'class\s+(\w+)',
            "C#":          r'(?:public|private|internal|abstract|sealed|\s)*class\s+(\w+)',
            "Swift":       r'(?:public\s+|private\s+|internal\s+|open\s+)?class\s+(\w+)',
            "Kotlin":      r'(?:data\s+|sealed\s+|abstract\s+|open\s+)?class\s+(\w+)',
            "Scala":       r'(?:case\s+)?class\s+(\w+)',
            "Objective-C": r'@interface\s+(\w+)',
        },
        "import": {
            "JavaScript":  r'(?:import\s+.+from\s+[\'"]([^\'"]+)[\'"]|require\s*\([\'"]([^\'"]+)[\'"]\))',
            "TypeScript":  r'import\s+.+from\s+[\'"]([^\'"]+)[\'"]',
            "Java":        r'import\s+([\w.]+)',
            "C":           r'#include\s*[<"]([^>"]+)[>"]',
            "C++":         r'#include\s*[<"]([^>"]+)[>"]',
            "C/C++ Header":r'#include\s*[<"]([^>"]+)[>"]',
            "C++ Header":  r'#include\s*[<"]([^>"]+)[>"]',
            "Go":          r'"([^"]+)"',
            "Rust":        r'(?:use\s+([\w:]+)|extern\s+crate\s+(\w+))',
            "Ruby":        r'require\s+[\'"]([^\'"]+)[\'"]',
            "PHP":         r'(?:use\s+([\w\\\\]+)|require(?:_once)?\s+[\'"]([^\'"]+)[\'"])',
            "C#":          r'using\s+([\w.]+)',
            "Swift":       r'import\s+(\w+)',
            "Kotlin":      r'import\s+([\w.]+)',
            "Kotlin Script":r'import\s+([\w.]+)',
            "Scala":       r'import\s+([\w.{},\s]+)',
            "Lua":         r'require\s*[(\'"]+([^\'")\s]+)',
            "Shell":       r'(?:source|\.)\s+([^\s;]+)',
            "Bash":        r'(?:source|\.)\s+([^\s;]+)',
            "R":           r'(?:library|require)\s*\(\s*[\'"]?(\w+)',
            "Objective-C": r'#import\s*[<"]([^>"]+)[>"]',
        },
    }

    def _analyze_generic(self, source: str, filename: str, result: AnalysisResult, comment_char: str) -> AnalysisResult:
        """对非 Python 语言进行基于正则的通用分析"""
        lang = result.language

        self._count_lines(source, result, comment_char)

        # 提取函数
        func_pattern = self._GENERIC_PATTERNS["function"].get(lang)
        if func_pattern:
            for match in re.finditer(func_pattern, source):
                name = next((g for g in match.groups() if g), None)
                if name:
                    lineno = source[:match.start()].count('\n') + 1
                    result.functions.append(FunctionInfo(
                        name=name, lineno=lineno, end_lineno=None,
                        args=[], decorators=[], calls=[],
                        complexity=1, docstring=None,
                    ))

        # 提取类
        cls_pattern = self._GENERIC_PATTERNS["class"].get(lang)
        if cls_pattern:
            for match in re.finditer(cls_pattern, source):
                name = next((g for g in match.groups() if g), None)
                if name:
                    lineno = source[:match.start()].count('\n') + 1
                    result.classes.append(ClassInfo(
                        name=name, lineno=lineno, end_lineno=None,
                        bases=[], methods=[], decorators=[],
                    ))

        # 提取导入
        imp_pattern = self._GENERIC_PATTERNS["import"].get(lang)
        if imp_pattern:
            for match in re.finditer(imp_pattern, source):
                module = next((g for g in match.groups() if g), None)
                if module:
                    lineno = source[:match.start()].count('\n') + 1
                    result.imports.append(ImportInfo(
                        module=module, names=[module.split(".")[-1]],
                        lineno=lineno, is_from=False,
                    ))

        # 近似圈复杂度估算
        branch_keywords = r'\b(if|else\s+if|elif|while|for|catch|except|case|switch)\b'
        logic_ops = r'(&&|\|\|)'
        for func in result.functions:
            func_start = func.lineno - 1
            lines = source.splitlines()
            func_end = len(lines)
            for other in result.functions:
                if other.lineno > func.lineno:
                    func_end = min(func_end, other.lineno - 1)
                    break
            func_text = "\n".join(lines[func_start:func_end])
            func.complexity = 1 + len(re.findall(branch_keywords, func_text)) + len(re.findall(logic_ops, func_text))

        # 构建 Code Graph
        result.code_graph = self._build_code_graph(result)
        return result

    def _count_lines(self, source: str, result: AnalysisResult, comment_char: str = "#"):
        """统计有效代码行与注释行（空行不计入任何类别）"""
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            elif stripped.startswith(comment_char):
                result.comment_lines += 1
            elif comment_char == "//" and stripped.startswith("/*"):
                result.comment_lines += 1
            else:
                result.code_lines += 1

    def _extract_imports(self, tree: ast.Module, result: AnalysisResult):
        """提取导入信息"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(
                        ImportInfo(
                            module=alias.name,
                            names=[alias.asname or alias.name],
                            lineno=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.asname or alias.name for alias in node.names]
                result.imports.append(
                    ImportInfo(module=module, names=names, lineno=node.lineno, is_from=True)
                )

    def _extract_classes(self, tree: ast.Module, result: AnalysisResult):
        """提取类信息"""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(ast.dump(base))

                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                decorators = self._get_decorator_names(node)
                docstring = ast.get_docstring(node)

                cls = ClassInfo(
                    name=node.name,
                    lineno=node.lineno,
                    end_lineno=getattr(node, "end_lineno", None),
                    bases=bases,
                    methods=methods,
                    decorators=decorators,
                    docstring=docstring,
                )
                result.classes.append(cls)

                # 提取方法
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        fi = self._parse_function(child, class_name=node.name)
                        result.functions.append(fi)

    def _extract_functions(self, tree: ast.Module, result: AnalysisResult):
        """提取顶层函数"""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fi = self._parse_function(node)
                result.functions.append(fi)

    def _parse_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, class_name: Optional[str] = None
    ) -> FunctionInfo:
        """解析单个函数"""
        args = [arg.arg for arg in node.args.args]
        decorators = self._get_decorator_names(node)
        calls = self._get_function_calls(node)
        complexity = self._calc_complexity(node)
        docstring = ast.get_docstring(node)

        return FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", None),
            args=args,
            decorators=decorators,
            calls=calls,
            complexity=complexity,
            docstring=docstring,
            is_method=class_name is not None,
            class_name=class_name,
        )

    def _get_decorator_names(self, node) -> list[str]:
        names = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                names.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                names.append(f"{ast.dump(dec)}")
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    names.append(dec.func.id)
        return names

    def _get_function_calls(self, node) -> list[str]:
        """提取函数体内的所有函数调用名称（去重）"""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return list(set(calls))

    def _calc_complexity(self, node) -> int:
        """计算 McCabe 圈复杂度

        规则：基础复杂度=1，每遇到一个分支节点（if/while/for/except）+1，
        布尔运算符（and/or）的每个额外操作数 +1，列表推导的 for 和 if 各 +1。
        """
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                complexity += len(child.ifs)
        return complexity

    def _extract_globals(self, tree: ast.Module, result: AnalysisResult):
        """提取全局变量"""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        result.global_variables.append(target.id)

    def _build_code_graph(self, result: AnalysisResult) -> str:
        """构建文本形式的 Code Graph

        生成的文本包含四个段落::

            [类]          类名(基类) 及其方法列表
            [函数]        独立顶层函数及其签名
            [调用关系]    函数 → 函数 的调用边
            [高复杂度警告] 圈复杂度 > 10 的函数

        该文本将嵌入评估 prompt，帮助 LLM 理解代码结构。
        """
        lines = []

        # 类结构
        for cls in result.classes:
            base_str = f"({', '.join(cls.bases)})" if cls.bases else ""
            lines.append(f"[类] {cls.name}{base_str}")
            for method in cls.methods:
                lines.append(f"  └── {cls.name}.{method}")

        # 独立函数
        standalone = [f for f in result.functions if not f.is_method]
        if standalone:
            lines.append("")
            lines.append("[函数]")
            for func in standalone:
                lines.append(f"  {func.name}({', '.join(func.args)})")

        # 调用关系
        call_edges = []
        all_func_names = {f.name for f in result.functions}
        for func in result.functions:
            caller = f"{func.class_name}.{func.name}" if func.class_name else func.name
            for callee in func.calls:
                if callee in all_func_names:
                    call_edges.append((caller, callee))

        if call_edges:
            lines.append("")
            lines.append("[调用关系]")
            for src, dst in call_edges:
                lines.append(f"  {src} -> {dst}")

        # 复杂度警告
        complex_funcs = [f for f in result.functions if f.complexity > 10]
        if complex_funcs:
            lines.append("")
            lines.append("[高复杂度警告]")
            for f in complex_funcs:
                name = f"{f.class_name}.{f.name}" if f.class_name else f.name
                lines.append(f"  {name}: 圈复杂度 = {f.complexity}")

        return "\n".join(lines) if lines else "（代码结构简单，无显著调用关系）"
