#!/usr/bin/env python3
"""Eval Agent CLI — 多语言代码评估与进化智能体命令行入口

支持三种输入模式（文件 / 目录 / 代码片段）和 Web 可视化界面。
评估流程：AST解析 → 7维评估 → Bug修复 → 代码改进 → 测试生成 → 经验总结。

用法示例::

    # 评估单个文件（Python / JS / Go / Rust / Java 等 16+ 语言）
    python3 main.py -f my_script.py
    python3 main.py -f app.js

    # 评估整个项目目录
    python3 main.py -d ./my_project

    # 启动 Web 可视化界面
    python3 main.py --web
    python3 main.py --web --port 9000

    # 评估代码片段
    python3 main.py -c "def add(a, b): return a + b"

    # 管道输入
    cat script.py | python3 main.py

    # 指定 LLM 并输出报告到文件
    python3 main.py -f code.py --model gpt-4 -o report.md

    # 附加自我校验
    python3 main.py -d ./src --self-check -v
"""

from __future__ import annotations

import argparse
import logging
import sys
import os

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AgentConfig, LLMConfig, MemoryConfig
from eval_agent.agent import EvalAgent


def setup_logging(verbose: bool = False):
    """配置全局日志格式与级别

    Args:
        verbose: True 时启用 DEBUG 级别，否则 INFO
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def read_source(args) -> tuple[str, str | None]:
    """从文件 / 命令行参数 / 标准输入读取待评估的源代码

    Returns:
        (source_code, file_path) 元组；代码片段和管道输入时 file_path 为 None
    """
    if args.file:
        path = os.path.abspath(args.file)
        if not os.path.isfile(path):
            print(f"错误：文件不存在 - {path}", file=sys.stderr)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), path
    elif args.code:
        return args.code, None
    elif not sys.stdin.isatty():
        return sys.stdin.read(), None
    else:
        print("错误：请通过 -f 指定文件、-c 提供代码，或通过管道输入", file=sys.stderr)
        sys.exit(1)


def build_config(args) -> AgentConfig:
    """从命令行参数构建配置"""
    llm_config = LLMConfig()
    if args.api_base:
        llm_config.api_base = args.api_base
    if args.api_key:
        llm_config.api_key = args.api_key
    if args.model:
        llm_config.model = args.model
    if args.temperature is not None:
        llm_config.temperature = args.temperature
    if args.max_tokens is not None:
        llm_config.max_tokens = args.max_tokens

    memory_config = MemoryConfig()
    if args.memory_dir:
        memory_config.memory_dir = args.memory_dir

    return AgentConfig(
        llm=llm_config,
        memory=memory_config,
        verbose=args.verbose,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Eval Agent — 面向多语言代码的评估与进化型智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
使用示例：
  %(prog)s -f my_script.py                    评估单个文件
  %(prog)s -d ./my_project                    评估整个目录（递归）
  %(prog)s -c "def add(a,b): return a+b"      评估代码片段
  cat script.py | %(prog)s                     管道输入
  %(prog)s -d ./src --self-check              目录评估 + 自我校验
  %(prog)s -f code.py --model gpt-4            指定 LLM 模型
  %(prog)s -d ./project -o report.md           输出报告到文件
  %(prog)s --web                               启动 Web 可视化界面
  %(prog)s --web --port 9000                   自定义端口

环境变量：
  EVAL_AGENT_API_BASE     LLM API 地址 (默认 http://localhost:11434/v1)
  EVAL_AGENT_API_KEY      API 密钥 (默认 ollama)
  EVAL_AGENT_MODEL        模型名称 (默认 qwen3-coder:30b)
  EVAL_AGENT_TEMPERATURE  采样温度 (默认 0.3)
  EVAL_AGENT_MAX_TOKENS   最大 token 数 (默认 8192)
  EVAL_AGENT_MEMORY_DIR   记忆存储目录 (默认 ./memory_store)
""",
    )

    # ---- 输入选项（三选一） ----
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-f", "--file", help="待评估的代码文件路径")
    input_group.add_argument("-d", "--directory", help="待评估的项目目录（递归扫描所有代码文件）")
    input_group.add_argument("-c", "--code", help="待评估的代码片段（直接传入字符串）")

    # ---- 输出选项 ----
    parser.add_argument("-o", "--output", help="将 Markdown 报告保存到指定文件")
    parser.add_argument("--self-check", action="store_true", help="启用自我校验（LLM 审核报告质量）")

    # ---- LLM 配置覆盖 ----
    parser.add_argument("--api-base", help="LLM API 端点地址（覆盖 EVAL_AGENT_API_BASE）")
    parser.add_argument("--api-key", help="LLM API 密钥（覆盖 EVAL_AGENT_API_KEY）")
    parser.add_argument("--model", help="模型名称（覆盖 EVAL_AGENT_MODEL）")
    parser.add_argument("--temperature", type=float, help="采样温度 0-1（覆盖 EVAL_AGENT_TEMPERATURE）")
    parser.add_argument("--max-tokens", type=int, help="最大生成 token 数（覆盖 EVAL_AGENT_MAX_TOKENS）")

    # ---- 记忆配置 ----
    parser.add_argument("--memory-dir", help="记忆持久化存储目录（覆盖 EVAL_AGENT_MEMORY_DIR）")

    # ---- Web 界面 ----
    parser.add_argument("--web", action="store_true", help="启动 Web 可视化界面（浏览器访问）")
    parser.add_argument("--host", default="127.0.0.1", help="Web 服务绑定地址 (默认 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Web 服务端口 (默认 8000)")

    # ---- 通用 ----
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志输出（DEBUG 级别）")
    parser.add_argument("--version", action="version", version="Eval Agent v0.2.0")

    args = parser.parse_args()
    setup_logging(args.verbose)

    # ── Web 模式 ──
    if args.web:
        try:
            import uvicorn
            from web.server import app
        except ImportError:
            print(
                "错误：Web 模式需要安装 fastapi 和 uvicorn\n"
                "  pip install fastapi 'uvicorn[standard]'",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Eval Agent Web 界面已启动: http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return

    # 构建配置与 Agent
    config = build_config(args)
    agent = EvalAgent(config)

    # 目录模式 vs 单文件模式
    try:
        if args.directory:
            # --- 目录级评估 ---
            dirpath = os.path.abspath(args.directory)
            if not os.path.isdir(dirpath):
                print(f"错误：目录不存在 - {dirpath}", file=sys.stderr)
                sys.exit(1)
            report = agent.run_directory(dirpath, self_check=args.self_check)
        else:
            # --- 单文件/代码片段评估 ---
            source, file_path = read_source(args)
            if not source.strip():
                print("错误：输入代码为空", file=sys.stderr)
                sys.exit(1)
            if args.self_check:
                report = agent.run_with_check(source, file_path)
            else:
                report = agent.run(source, file_path)
    except Exception as e:
        logging.error("评估失败: %s", e)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # 输出结果
    if args.output:
        out_path = os.path.abspath(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已保存至: {out_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
