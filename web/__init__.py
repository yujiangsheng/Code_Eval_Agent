"""Eval Agent Web 模块 — FastAPI REST API + 可视化前端

提供基于浏览器的可视化界面，支持目录扫描、深度评估、
代码结构图、统计图表、知识图谱和四层记忆库管理。

API 端点::

    GET  /                   前端页面
    POST /api/scan            快速扫描目录（纯 AST，不调 LLM）
    POST /api/evaluate        LLM 深度评估（SSE 流式）
    POST /api/analyze/file    单文件 AST 分析
    GET  /api/knowledge       获取持久知识库
    GET  /api/memory          获取四层记忆
    POST /api/memory/external 添加外部记忆
    DELETE /api/memory/external 删除外部记忆
    GET  /api/browse          浏览本地目录
    POST /api/shutdown        终止服务

启动方式::

    python3 main.py --web                  # 默认 127.0.0.1:8000
    python3 main.py --web --port 9000      # 自定义端口
"""
