"""Eval Agent Web 服务 — FastAPI REST API + 可视化仪表盘

核心能力:
  1. **前端页面**    — vis-network / Chart.js / marked.js 可视化仪表盘
  2. **快速扫描**    — 纯 AST/正则分析，毫秒级，无 LLM 调用
  3. **深度评估**    — SSE 流式返回 LLM 评估进度与最终报告
  4. **记忆管理**    — 四层记忆（工作/长期/持久/外部）查询与维护
  5. **知识图谱**    — 持久知识库分类展示与图谱可视化
  6. **目录浏览**    — 文件系统目录结构浏览

启动方式::

    python3 main.py --web                  # 默认 127.0.0.1:8000
    python3 main.py --web --port 9000      # 自定义端口

API 端点:
    GET  /                     前端页面
    POST /api/scan             快速扫描目录（AST，无 LLM）
    POST /api/evaluate         LLM 深度评估（SSE 流式返回）
    POST /api/analyze/file     单文件 AST 分析
    GET  /api/knowledge        获取持久知识库
    GET  /api/memory           获取四层记忆
    POST /api/memory/external  添加外部记忆
    DEL  /api/memory/external  删除外部记忆
    GET  /api/browse           浏览本地目录
    POST /api/shutdown         终止服务
"""

from __future__ import annotations

import json
import logging
import os
import queue
import sys
import threading
from pathlib import Path
from typing import Optional

# 将项目根目录加入 path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import AgentConfig, LLMConfig, MemoryConfig
from eval_agent.analyzer import CodeAnalyzer, AnalysisResult
from eval_agent.scanner import DirectoryScanner, ProjectAnalysis
from eval_agent.agent import EvalAgent
from eval_agent.memory import LongTermMemory, PersistentKnowledge, WorkingMemory

logger = logging.getLogger(__name__)

# ── 全局状态 ──────────────────────────────────────────────

# 最近一次评估的工作记忆快照
_last_working_memory: dict = {}

# ── FastAPI 应用 ──────────────────────────────────────────────

app = FastAPI(title="Eval Agent", version="0.2.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── 请求模型 ──────────────────────────────────────────────────

class ScanRequest(BaseModel):
    directory: str


class EvaluateRequest(BaseModel):
    directory: Optional[str] = None
    file: Optional[str] = None
    code: Optional[str] = None
    requirements: str = ""
    focus: list[str] = []
    self_check: bool = False


class FileAnalyzeRequest(BaseModel):
    file_path: str


# ── 路由 ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面"""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/browse")
async def browse_directory(path: str = "~"):
    """浏览本地文件系统目录结构，返回子目录列表"""
    try:
        target = os.path.expanduser(path)
        target = os.path.abspath(target)
        if not os.path.isdir(target):
            return JSONResponse(
                {"success": False, "error": f"目录不存在: {target}"},
                status_code=400,
            )
        entries = []
        try:
            for name in sorted(os.listdir(target)):
                if name.startswith("."):
                    continue  # 隐藏文件/目录
                full = os.path.join(target, name)
                if os.path.isdir(full):
                    entries.append({"name": name, "path": full, "type": "dir"})
        except PermissionError:
            pass
        parent = os.path.dirname(target) if target != "/" else None
        return {
            "success": True,
            "current": target,
            "parent": parent,
            "entries": entries,
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/shutdown")
async def shutdown_server():
    """终止所有后台服务并强制退出进程"""
    logger.info("收到关闭请求，正在终止所有后台服务...")

    def _force_exit():
        import signal
        pid = os.getpid()
        # 终止当前进程组内的所有子进程
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        logger.info("服务器已停止。")
        os._exit(0)

    # 延迟 0.5 秒再退出，让 HTTP 响应先发回前端
    timer = threading.Timer(0.5, _force_exit)
    timer.daemon = True
    timer.start()
    return {"success": True, "message": "服务器正在关闭..."}


@app.post("/api/scan")
async def scan_directory(req: ScanRequest):
    """快速扫描目录 — 仅 AST 分析，不调用 LLM，毫秒级完成"""
    try:
        directory = os.path.abspath(req.directory)
        if not os.path.isdir(directory):
            return JSONResponse(
                {"success": False, "error": f"目录不存在: {directory}"},
                status_code=400,
            )

        scanner = DirectoryScanner()
        project = scanner.scan(directory)

        return {
            "success": True,
            "root_dir": project.root_dir,
            "metrics": _extract_metrics(project),
            "files": _extract_files(project),
            "code_graph": _build_code_graph_data(project),
            "complexity_ranking": project.complexity_ranking[:30],
            "module_dependencies": project.module_dependencies,
            "circular_deps": project.circular_deps,
            "duplicate_names": project.duplicate_names,
            "syntax_errors": project.all_syntax_errors,
            "cross_file_graph_text": project.cross_file_graph,
        }
    except Exception as e:
        logger.error("扫描失败: %s", e, exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/evaluate")
async def evaluate_project(req: EvaluateRequest):
    """LLM 深度评估 — 通过 SSE 流式返回进度与最终报告"""
    msg_queue: queue.Queue = queue.Queue()
    result_holder: dict = {"report": None, "error": None}

    # 拦截 eval_agent 日志以捕获进度
    class _ProgressHandler(logging.Handler):
        def emit(self, record):
            msg_queue.put({"type": "progress", "message": self.format(record)})

    handler = _ProgressHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    eval_logger = logging.getLogger("eval_agent")
    eval_logger.addHandler(handler)

    def _run():
        try:
            config = AgentConfig()
            agent = EvalAgent(config)

            # 注入用户自定义要求到评估 prompt
            _inject_requirements(agent, req.requirements, req.focus)

            if req.directory:
                d = os.path.abspath(req.directory)
                result_holder["report"] = agent.run_directory(
                    d, self_check=req.self_check
                )
            elif req.file:
                path = os.path.abspath(req.file)
                with open(path, "r", encoding="utf-8") as f:
                    source = f.read()
                if req.self_check:
                    result_holder["report"] = agent.run_with_check(source, path)
                else:
                    result_holder["report"] = agent.run(source, path)
            elif req.code:
                result_holder["report"] = agent.run(req.code)
            else:
                result_holder["error"] = "请提供 directory、file 或 code 参数"
            # 评估完成后捕获工作记忆快照
            _capture_working_memory(agent)
        except Exception as e:
            logger.error("评估失败: %s", e, exc_info=True)
            result_holder["error"] = str(e)
        finally:
            eval_logger.removeHandler(handler)
            msg_queue.put(None)  # 结束哨兵

    # 后台线程执行评估
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    async def _event_stream():
        while True:
            try:
                msg = msg_queue.get(timeout=1.0)
                if msg is None:
                    # 评估完成
                    if result_holder["error"]:
                        payload = {"type": "error", "error": result_holder["error"]}
                    else:
                        payload = {"type": "done", "report": result_holder["report"]}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break
                else:
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@app.post("/api/analyze/file")
async def analyze_single_file(req: FileAnalyzeRequest):
    """单文件 AST 分析（不调用 LLM）"""
    try:
        path = os.path.abspath(req.file_path)
        if not os.path.isfile(path):
            return JSONResponse(
                {"success": False, "error": f"文件不存在: {path}"},
                status_code=400,
            )
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()

        analyzer = CodeAnalyzer()
        result = analyzer.analyze(source, filename=os.path.basename(path))

        return {
            "success": True,
            "file_path": path,
            "analysis": result.to_dict(),
            "code_graph_text": result.code_graph,
            "graph_data": _build_single_file_graph(result, os.path.basename(path)),
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/knowledge")
async def get_knowledge():
    """获取持久知识库全部内容"""
    try:
        config = MemoryConfig()
        knowledge = PersistentKnowledge(config)
        data = {}
        for cat in knowledge.categories:
            data[cat] = knowledge.get_category(cat)

        # 构建知识图谱数据
        graph = _build_knowledge_graph(data)
        return {"success": True, "categories": data, "graph": graph}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/memory")
async def get_memory():
    """获取四类记忆：工作 / 长期 / 持久 / 外部"""
    try:
        config = MemoryConfig()

        # 工作记忆
        working = _last_working_memory

        # 长期记忆
        ltm = LongTermMemory(config)
        long_term_entries = ltm.search(limit=100)

        # 持久记忆（知识库）
        pk = PersistentKnowledge(config)
        persistent = {}
        for cat in pk.categories:
            persistent[cat] = pk.get_category(cat)

        # 外部记忆
        external = _load_external_memory(config)

        return {
            "success": True,
            "working": working,
            "long_term": {"total": len(long_term_entries), "entries": long_term_entries},
            "persistent": persistent,
            "external": {"total": len(external), "entries": external},
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


class ExternalMemoryRequest(BaseModel):
    content: str = ""
    index: int = -1


@app.post("/api/memory/external")
async def add_external_memory_entry(req: ExternalMemoryRequest):
    """添加外部记忆条目"""
    try:
        config = MemoryConfig()
        entries = _load_external_memory(config)
        from datetime import datetime
        entries.append({
            "content": req.content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _save_external_memory(config, entries)
        return {"success": True}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.delete("/api/memory/external")
async def delete_external_memory_entry(req: ExternalMemoryRequest):
    """删除外部记忆条目"""
    try:
        config = MemoryConfig()
        entries = _load_external_memory(config)
        if 0 <= req.index < len(entries):
            entries.pop(req.index)
        _save_external_memory(config, entries)
        return {"success": True}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ── 辅助函数 ──────────────────────────────────────────────────

def _external_memory_path(config: MemoryConfig) -> str:
    return os.path.join(config.memory_dir, config.external_memory_file)


def _load_external_memory(config: MemoryConfig) -> list[dict]:
    path = _external_memory_path(config)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_external_memory(config: MemoryConfig, entries: list[dict]):
    os.makedirs(config.memory_dir, exist_ok=True)
    with open(_external_memory_path(config), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _capture_working_memory(agent: EvalAgent):
    """评估完成后，将工作记忆快照保存到全局状态"""
    global _last_working_memory
    wm = agent.working_memory
    from datetime import datetime
    _last_working_memory = {
        "file_path": wm.file_path or "",
        "language": wm.language,
        "code_length": len(wm.source_code),
        "issues_count": len(wm.issues),
        "summary": wm.summary(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _inject_requirements(agent: EvalAgent, requirements: str, focus: list[str]):
    """将用户自定义要求注入到评估器的 system prompt 中"""
    if not requirements and not focus:
        return

    import eval_agent.evaluator as ev_mod

    extra = "\n\n--- 用户特别要求 ---\n"
    if requirements:
        extra += f"{requirements}\n"
    if focus:
        extra += f"重点关注维度: {', '.join(focus)}\n"

    # 临时追加，评估结束后由 GC 处理（agent 为局部变量）
    original = ev_mod.EVALUATION_SYSTEM_PROMPT
    ev_mod.EVALUATION_SYSTEM_PROMPT = original + extra

    # 同时追加到 deep interpret 的 prompt（目录评估时）
    agent._user_requirements = extra


def _extract_metrics(project: ProjectAnalysis) -> dict:
    comment_ratio = 0.0
    if project.total_code_lines > 0:
        comment_ratio = round(
            project.total_comment_lines / project.total_code_lines * 100, 1
        )
    return {
        "total_files": project.total_files,
        "total_lines": project.total_lines,
        "total_code_lines": project.total_code_lines,
        "total_comment_lines": project.total_comment_lines,
        "total_functions": project.total_functions,
        "total_classes": project.total_classes,
        "total_imports": project.total_imports,
        "comment_ratio": comment_ratio,
    }


def _extract_files(project: ProjectAnalysis) -> list[dict]:
    files = []
    for fa in project.files:
        a = fa.analysis
        max_complexity = max((f.complexity for f in a.functions), default=1)
        files.append({
            "path": fa.relative_path,
            "lines": a.total_lines,
            "code_lines": a.code_lines,
            "comment_lines": a.comment_lines,
            "functions": len(a.functions),
            "classes": len(a.classes),
            "imports": len(a.imports),
            "max_complexity": max_complexity,
            "syntax_errors": a.syntax_errors,
            "size_bytes": fa.size_bytes,
        })
    return files


def _build_code_graph_data(project: ProjectAnalysis) -> dict:
    """将 ProjectAnalysis 转换为 vis.js 兼容的 nodes/edges 格式"""
    nodes = []
    edges = []
    node_ids = set()

    def _add_node(nid, label, group, **extra):
        if nid not in node_ids:
            node_ids.add(nid)
            node = {"id": nid, "label": label, "group": group}
            node.update(extra)
            nodes.append(node)

    # 文件节点
    for fa in project.files:
        fid = f"file:{fa.relative_path}"
        size = 10 + min(fa.analysis.code_lines / 20, 40)
        _add_node(fid, fa.relative_path, "file", value=int(size))

        # 类节点
        for cls in fa.analysis.classes:
            cid = f"class:{fa.relative_path}:{cls.name}"
            _add_node(cid, cls.name, "class", title=f"类 {cls.name}\n基类: {cls.bases}")
            edges.append({"from": fid, "to": cid, "type": "contains", "color": "#475569"})

            # 方法节点
            for method in cls.methods:
                mid = f"method:{fa.relative_path}:{cls.name}.{method}"
                _add_node(mid, f".{method}", "method")
                edges.append({"from": cid, "to": mid, "type": "contains", "color": "#334155"})

        # 独立函数节点
        for func in fa.analysis.functions:
            if func.is_method:
                continue
            fnid = f"func:{fa.relative_path}:{func.name}"
            _add_node(
                fnid, func.name, "function",
                title=f"{func.name}({', '.join(func.args)})\n复杂度: {func.complexity}",
            )
            edges.append({"from": fid, "to": fnid, "type": "contains", "color": "#475569"})

    # 模块依赖边（多语言兼容）
    from eval_agent.scanner import DEFAULT_EXTENSIONS
    def _strip_ext(path: str) -> str:
        for ext in sorted(DEFAULT_EXTENSIONS, key=len, reverse=True):
            if path.endswith(ext):
                return path[:-len(ext)]
        return path

    for mod, deps in project.module_dependencies.items():
        from_candidates = [f"file:{fa.relative_path}" for fa in project.files
                          if _strip_ext(fa.relative_path.replace(os.sep, ".")) == mod
                          or fa.relative_path.replace(os.sep, ".").removesuffix(".__init__") == mod]
        for dep in deps:
            to_candidates = [f"file:{fa.relative_path}" for fa in project.files
                            if _strip_ext(fa.relative_path.replace(os.sep, ".")) == dep
                            or fa.relative_path.replace(os.sep, ".").removesuffix(".__init__") == dep]
            for fc in from_candidates:
                for tc in to_candidates:
                    if fc in node_ids and tc in node_ids:
                        edges.append({
                            "from": fc, "to": tc, "type": "import",
                            "dashes": True, "color": "#64748b",
                            "arrows": "to",
                        })

    # 跨文件调用边
    defined_in: dict[str, str] = {}
    for fa in project.files:
        for func in fa.analysis.functions:
            if not func.is_method:
                defined_in[func.name] = fa.relative_path
        for cls in fa.analysis.classes:
            defined_in[cls.name] = fa.relative_path

    for fa in project.files:
        for func in fa.analysis.functions:
            for callee in func.calls:
                if callee in defined_in and defined_in[callee] != fa.relative_path:
                    caller_id = (
                        f"method:{fa.relative_path}:{func.class_name}.{func.name}"
                        if func.is_method
                        else f"func:{fa.relative_path}:{func.name}"
                    )
                    callee_file = defined_in[callee]
                    callee_id = f"func:{callee_file}:{callee}"
                    if caller_id in node_ids and callee_id in node_ids:
                        edges.append({
                            "from": caller_id, "to": callee_id, "type": "call",
                            "color": "#f59e0b", "arrows": "to",
                        })

    # 继承边
    class_file: dict[str, str] = {}
    for fa in project.files:
        for cls in fa.analysis.classes:
            class_file[cls.name] = fa.relative_path

    for fa in project.files:
        for cls in fa.analysis.classes:
            for base in cls.bases:
                if base in class_file:
                    child_id = f"class:{fa.relative_path}:{cls.name}"
                    parent_id = f"class:{class_file[base]}:{base}"
                    if child_id in node_ids and parent_id in node_ids:
                        edges.append({
                            "from": child_id, "to": parent_id, "type": "inherit",
                            "color": "#a855f7", "arrows": "to", "width": 2,
                        })

    return {"nodes": nodes, "edges": edges}


def _build_single_file_graph(analysis: AnalysisResult, filename: str) -> dict:
    """为单个文件构建 vis.js 图数据"""
    nodes = []
    edges = []

    fid = f"file:{filename}"
    nodes.append({"id": fid, "label": filename, "group": "file", "value": 30})

    for cls in analysis.classes:
        cid = f"class:{cls.name}"
        nodes.append({"id": cid, "label": cls.name, "group": "class"})
        edges.append({"from": fid, "to": cid})

    for func in analysis.functions:
        if func.is_method:
            mid = f"method:{func.class_name}.{func.name}"
            nodes.append({"id": mid, "label": f".{func.name}", "group": "method"})
            cid = f"class:{func.class_name}"
            edges.append({"from": cid, "to": mid})
        else:
            fnid = f"func:{func.name}"
            nodes.append({"id": fnid, "label": func.name, "group": "function"})
            edges.append({"from": fid, "to": fnid})

    # 内部调用边
    all_names = {f.name for f in analysis.functions}
    for func in analysis.functions:
        caller = (
            f"method:{func.class_name}.{func.name}" if func.is_method
            else f"func:{func.name}"
        )
        for callee in func.calls:
            if callee in all_names and callee != func.name:
                target = f"func:{callee}"
                edges.append({"from": caller, "to": target, "color": "#f59e0b", "arrows": "to"})

    return {"nodes": nodes, "edges": edges}


def _build_knowledge_graph(data: dict[str, list[str]]) -> dict:
    """将知识库构建为 vis.js 图数据"""
    nodes = []
    edges = []

    cat_colors = {
        "python_best_practices": "#3b82f6",
        "common_bug_patterns": "#ef4444",
        "optimization_strategies": "#22c55e",
        "security_checklist": "#f59e0b",
    }

    for cat, entries in data.items():
        color = cat_colors.get(cat, "#8b5cf6")
        cat_label = cat.replace("_", " ").title()
        nodes.append({
            "id": f"cat:{cat}", "label": cat_label,
            "group": "category", "color": color,
            "value": 30 + len(entries) * 2,
            "font": {"size": 16, "color": "#e2e8f0"},
        })
        for i, entry in enumerate(entries):
            eid = f"entry:{cat}:{i}"
            short_label = entry[:30] + "…" if len(entry) > 30 else entry
            nodes.append({
                "id": eid, "label": short_label,
                "group": "entry", "title": entry,
                "color": color, "value": 8,
                "font": {"size": 10, "color": "#94a3b8"},
            })
            edges.append({"from": f"cat:{cat}", "to": eid, "color": "#334155"})

    return {"nodes": nodes, "edges": edges}
