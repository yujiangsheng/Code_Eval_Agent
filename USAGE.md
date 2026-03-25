# Eval Agent 详细用法指南

> **v0.2.0** — 多语言代码评估与进化型智能体

本文档提供 Eval Agent 的详细用法说明、Web 界面操作、多语言评估、高级配置与常见问题解答。

---

## 目录

1. [安装与环境准备](#1-安装与环境准备)
2. [基础使用](#2-基础使用)
3. [多语言评估](#3-多语言评估)
4. [高级功能](#4-高级功能)
5. [Web 可视化界面](#5-web-可视化界面)
6. [LLM 配置](#6-llm-配置)
7. [Python API 使用](#7-python-api-使用)
8. [四层记忆系统](#8-四层记忆系统)
9. [示例文件](#9-示例文件)
10. [常见问题](#10-常见问题)
11. [版本信息](#11-版本信息)

---

## 1. 安装与环境准备

### 前置条件

- Python 3.9+
- pip
- （可选）[Ollama](https://ollama.ai) — 用于本地 LLM 推理

### 安装步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd Code_Eval_Agent

# 2. 安装 Python 依赖（仅 3 个包）
pip install -r requirements.txt
# 安装内容: openai >= 1.0.0, fastapi, uvicorn

# 3.（可选）安装并启动 Ollama
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
ollama pull qwen3-coder:30b
```

### 验证安装

```bash
python3 main.py --version
# 输出: Eval Agent v0.2.0

python3 main.py --help
```

---

## 2. 基础使用

### 2.1 评估单个文件

```bash
python3 main.py -f examples/sample_code.py
```

输出为 8 章节 Markdown 报告，包含评分、问题清单、修复方案、改进代码和测试用例。语言根据文件扩展名自动识别。

### 2.2 评估代码片段

```bash
python3 main.py -c "
def binary_search(arr, target):
    left, right = 0, len(arr)
    while left < right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid
    return -1
"
```

### 2.3 管道输入

```bash
cat my_script.py | python3 main.py
# 或
echo 'def f(x): return x * 2' | python3 main.py
```

### 2.4 评估整个项目

```bash
python3 main.py -d ./my_project
```

输出 9 章节项目级报告，包含架构评估、依赖分析、复杂度排行和 Top-5 改进建议。支持 25+ 文件扩展名的递归扫描。

### 2.5 保存报告到文件

```bash
python3 main.py -f code.py -o report.md
python3 main.py -d ./src -o project_report.md
```

---

## 3. 多语言评估

v0.2.0 支持 **16+ 编程语言**，语言根据文件扩展名自动识别：

### 3.1 各语言评估示例

```bash
# Python（深度 AST 分析）
python3 main.py -f app.py

# JavaScript / TypeScript
python3 main.py -f app.js
python3 main.py -f component.tsx

# Java
python3 main.py -f Main.java

# Go
python3 main.py -f main.go

# Rust
python3 main.py -f lib.rs

# C / C++
python3 main.py -f program.c
python3 main.py -f solver.cpp

# Ruby
python3 main.py -f app.rb

# PHP
python3 main.py -f index.php

# Shell 脚本
python3 main.py -f deploy.sh

# Swift / Kotlin / Scala / C# / Lua / R / Objective-C
python3 main.py -f ViewController.swift
python3 main.py -f App.kt
```

### 3.2 分析深度说明

| 分析层 | Python | 其他语言 |
|--------|--------|---------|
| AST 解析 | ✅ `ast` 模块深度分析 | ✅ 正则模式提取 |
| 函数/类提取 | ✅ 完整（含装饰器、嵌套） | ✅ 基础（函数、类、接口） |
| 导入分析 | ✅ import / from-import | ✅ 语言特定模式 |
| 圈复杂度 | ✅ McCabe 精确计算 | ✅ 正则近似计算 |
| LLM 评估 | ✅ 7 维度深度评估 | ✅ 7 维度深度评估 |
| 测试框架 | pytest | 自动选择（Jest/JUnit/go test 等） |

### 3.3 混合语言项目

评估包含多种语言的项目时，目录扫描会递归发现所有受支持文件：

```bash
# 扫描整个全栈项目（Python + JS + Go + ...）
python3 main.py -d ./fullstack-project -o report.md
```

扫描器自动过滤 `node_modules`、`__pycache__`、`.git`、`venv`、`build` 等构建目录。

---

## 4. 高级功能

### 4.1 自我校验模式

```bash
python3 main.py -f code.py --self-check
```

在生成报告后，额外调用 LLM 审核报告质量，检查：
- 是否遗漏了重要问题
- 修复方案是否引入新 Bug
- 建议是否符合目标语言最佳实践
- 是否存在更优解

### 4.2 详细日志

```bash
python3 main.py -f code.py -v
```

启用 DEBUG 级别日志，输出每个步骤的详细过程，包括 LLM 调用信息和语言检测结果。

### 4.3 组合使用

```bash
# 完整组合: 目录评估 + 自我校验 + 详细日志 + 输出文件
python3 main.py -d ./my_project --self-check -v -o full_report.md
```

---

## 5. Web 可视化界面

### 5.1 启动 Web 界面

```bash
# 默认配置（127.0.0.1:8000）
python3 main.py --web

# 自定义地址和端口
python3 main.py --web --host 0.0.0.0 --port 9000
```

启动后在浏览器访问 `http://127.0.0.1:8000`。

### 5.2 六大功能面板

#### 🏠 控制台
- 输入项目路径（支持本地浏览器选择）
- 点击「快速扫描」执行纯 AST 分析（不调 LLM，毫秒级响应）
- 查看文件统计（总文件数、总行数、语言分布）
- 问题列表（语法错误、重名冲突、安全风险）

#### 🔗 Code Graph
- 交互式代码结构图（基于 vis-network）
- 节点类型：文件（蓝色）→ 类（橙色）→ 函数（绿色）→ 方法（浅绿）
- 支持拖拽、缩放、筛选
- 悬停显示详细信息（行号、复杂度、参数）

#### 📊 统计分析
- 代码行数分布（柱状图）
- 文件大小分布
- 圈复杂度排行（Top 20）
- 代码/注释比例（饼图）

#### 📝 深度评估
- LLM 驱动的完整评估（SSE 实时流式进度）
- 支持自定义评估要求和评估焦点
- 实时显示评估步骤进度
- 评估完成后自动保存工作记忆

#### 🧠 知识图谱
- 持久知识库的分类展示
- 交互式图谱可视化（类别→条目）
- 四类内置知识的浏览

#### 📚 记忆库
- **工作记忆** 标签页：查看当前/最近评估的中间结果
- **长期记忆** 标签页：浏览积累的 Bug 模式和优化经验
- **持久记忆** 标签页：查看内置最佳实践知识
- **外部记忆** 标签页：手动添加/删除用户自定义笔记

### 5.3 退出服务

点击侧边栏底部的「退出」按钮，或直接 `Ctrl+C` 终止终端进程。

### 5.4 REST API 端点

Web 界面的所有功能均可通过 REST API 直接调用：

```bash
# 快速扫描目录
curl -X POST http://127.0.0.1:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "./my_project"}'

# LLM 深度评估（返回 SSE 流）
curl -X POST http://127.0.0.1:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"path": "./my_project", "requirements": "重点关注安全性"}'

# 获取四层记忆
curl http://127.0.0.1:8000/api/memory

# 添加外部记忆
curl -X POST http://127.0.0.1:8000/api/memory/external \
  -H "Content-Type: application/json" \
  -d '{"content": "项目要求: 所有函数必须有类型注解"}'

# 删除外部记忆
curl -X DELETE http://127.0.0.1:8000/api/memory/external \
  -H "Content-Type: application/json" \
  -d '{"index": 0}'

# 获取持久知识库
curl http://127.0.0.1:8000/api/knowledge

# 浏览本地目录
curl "http://127.0.0.1:8000/api/browse?path=./src"

# 终止服务
curl -X POST http://127.0.0.1:8000/api/shutdown
```

---

## 6. LLM 配置

### 6.1 使用本地 Ollama（默认）

无需额外配置，确保 Ollama 运行并已拉取模型即可：

```bash
ollama serve &
ollama pull qwen3-coder:30b
python3 main.py -f code.py
```

### 6.2 使用 OpenAI

```bash
python3 main.py -f code.py \
  --api-base https://api.openai.com/v1 \
  --api-key sk-xxx \
  --model gpt-4
```

或通过环境变量：

```bash
export EVAL_AGENT_API_BASE=https://api.openai.com/v1
export EVAL_AGENT_API_KEY=sk-xxx
export EVAL_AGENT_MODEL=gpt-4o
python3 main.py -f code.py
```

### 6.3 使用其他兼容服务

任何兼容 OpenAI Chat Completions API 的服务均可使用：

```bash
# vLLM
python3 main.py -f code.py --api-base http://localhost:8000/v1

# LiteLLM
python3 main.py -f code.py --api-base http://localhost:4000/v1

# Azure OpenAI
python3 main.py -f code.py \
  --api-base https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT \
  --api-key YOUR_KEY
```

### 6.4 调节生成参数

```bash
# 降低温度获得更确定的输出
python3 main.py -f code.py --temperature 0.1

# 增加 token 上限以处理大文件
python3 main.py -f code.py --max-tokens 16384
```

### 6.5 环境变量完整列表

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `EVAL_AGENT_API_BASE` | LLM API 端点 | `http://localhost:11434/v1` |
| `EVAL_AGENT_API_KEY` | API 密钥 | `ollama` |
| `EVAL_AGENT_MODEL` | 模型名称 | `qwen3-coder:30b` |
| `EVAL_AGENT_TEMPERATURE` | 采样温度 | `0.3` |
| `EVAL_AGENT_MAX_TOKENS` | 最大 token 数 | `8192` |
| `EVAL_AGENT_TIMEOUT` | HTTP 超时（秒） | `120` |
| `EVAL_AGENT_MEMORY_DIR` | 记忆存储目录 | `./memory_store` |

优先级: **命令行参数 > 环境变量 > 默认值**

---

## 7. Python API 使用

### 7.1 基础用法

```python
from eval_agent import EvalAgent

agent = EvalAgent()

# 评估源代码字符串（自动识别语言）
source = open("my_script.py").read()
report = agent.run(source, "my_script.py")
print(report)
```

### 7.2 目录评估

```python
report = agent.run_directory("./src")
print(report)
```

### 7.3 自定义配置

```python
from config import AgentConfig, LLMConfig, MemoryConfig

config = AgentConfig(
    llm=LLMConfig(
        api_base="https://api.openai.com/v1",
        api_key="sk-xxx",
        model="gpt-4o",
        temperature=0.2,
        max_tokens=16384,
    ),
    memory=MemoryConfig(
        memory_dir="/tmp/eval_agent_memory",
    ),
    verbose=True,
)

agent = EvalAgent(config)
report = agent.run(source)
```

### 7.4 自我校验

```python
# 生成报告后额外进行 LLM 自审
report = agent.run_with_check(source, "my_script.py")
```

### 7.5 访问中间结果

```python
agent = EvalAgent()
report = agent.run(source)

# 访问工作记忆中的中间结果
wm = agent.working_memory
print("评估得分:", wm.evaluation.get("overall_score"))
print("问题数:", len(wm.issues))
print("Code Graph:\n", wm.code_graph)
```

### 7.6 纯静态分析（不调 LLM）

```python
from eval_agent.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer()

# 分析 Python 文件
result = analyzer.analyze(open("code.py").read(), "code.py")
print(result.code_graph)         # Code Graph 文本
print(result.to_dict())          # 完整分析数据

# 分析其他语言文件
result = analyzer.analyze(open("app.js").read(), "app.js")
print(f"语言: {result.language}")
print(f"函数数: {len(result.functions)}")
```

### 7.7 操作记忆系统

```python
from eval_agent.memory import LongTermMemory, PersistentKnowledge
from config import MemoryConfig

config = MemoryConfig()

# 查看长期记忆
ltm = LongTermMemory(config)
print(f"已积累 {ltm.size} 条经验")
results = ltm.search(keywords=["排序", "算法"])
print(ltm.format_for_prompt(results))

# 扩展知识库
knowledge = PersistentKnowledge(config)
knowledge.add_entry("python_best_practices",
    "使用 match-case 替代长 if-elif 链(Python 3.10+)")
print(knowledge.format_all())
```

---

## 8. 四层记忆系统

### 8.1 架构概览

| 层级 | 类 / 存储 | 生命周期 | 内容 |
|------|-----------|----------|------|
| **工作记忆** | `WorkingMemory` | 单轮任务 | 当前代码、AST、Code Graph、评估上下文 |
| **长期记忆** | `LongTermMemory` | 跨任务持久化 | Bug 模式、优化策略、代码结构经验 |
| **持久知识** | `PersistentKnowledge` | 永久 | 编码规范、安全清单、常见陷阱（四类内置） |
| **外部记忆** | `external_memory.json` | 永久 | 用户手动添加的笔记与参考上下文 |

### 8.2 记忆流转

```
单轮任务开始 → 初始化工作记忆
  → 各步骤写入中间结果（AST → 评估 → 修复 → 测试）
  → 任务结束时 LLM 提炼经验
  → 写入长期记忆（JSON 持久化）
  → 后续任务检索相关经验（关键词匹配）
  → LRU 淘汰（超过 500 条时）
```

### 8.3 持久知识库内置类别

| 类别键名 | 内容 | 示例 |
|---------|------|------|
| `python_best_practices` | Python 最佳实践 | PEP 8、类型提示、资源管理 |
| `common_bug_patterns` | 常见 Bug 模式 | 可变默认参数、并发竞态、None 处理 |
| `optimization_strategies` | 优化策略 | 缓存、数据结构选择、异步 I/O |
| `security_checklist` | 安全清单 | SQL 注入、XSS、命令注入、SSRF |

### 8.4 通过 Web 管理外部记忆

在 Web 界面的「记忆库 → 外部记忆」标签页中：
- 输入文本并点击「添加」按钮创建新条目
- 每条记录展示添加时间和内容
- 点击「删除」按钮移除不需要的条目

也可通过 API 操作：
```bash
# 添加
curl -X POST http://127.0.0.1:8000/api/memory/external \
  -H "Content-Type: application/json" \
  -d '{"content": "所有 API 接口必须添加鉴权"}'

# 删除（0-indexed）
curl -X DELETE http://127.0.0.1:8000/api/memory/external \
  -H "Content-Type: application/json" \
  -d '{"index": 0}'
```

### 8.5 记忆存储位置

默认在项目根目录的 `memory_store/` 下：

```
memory_store/
├── long_term_memory.json       # 长期记忆
├── persistent_knowledge.json   # 持久知识库
└── external_memory.json        # 外部记忆
```

可通过 `EVAL_AGENT_MEMORY_DIR` 环境变量或 `MemoryConfig(memory_dir=...)` 自定义路径。

---

## 9. 示例文件

项目提供三个精心设计的示例文件，覆盖不同的代码问题场景：

| 文件 | 问题类型 | 检测能力展示 |
|------|---------|-------------|
| `examples/sample_code.py` | 算法 Bug、边界缺失 | 冒泡排序无优化、空列表 IndexError、除零错误 |
| `examples/web_handler.py` | 安全漏洞 | SQL 注入、命令注入、路径遍历、不安全反序列化、硬编码密钥 |
| `examples/data_processor.py` | 性能问题 | O(n²) 重复检测、字符串拼接、无缓存递归、不必要深拷贝 |

### 逐个评估

```bash
python3 main.py -f examples/sample_code.py
python3 main.py -f examples/web_handler.py
python3 main.py -f examples/data_processor.py
```

### 整体评估

```bash
python3 main.py -d examples/ -o examples_report.md
```

### 结合高级功能

```bash
# 完整评估: 示例目录 + 自我校验 + 详细日志 + 报告输出
python3 main.py -d examples/ --self-check -v -o examples_full_report.md
```

---

## 10. 常见问题

### Q: 遇到 "LLM 调用失败" 错误？

确保 Ollama 正在运行并且模型已拉取：
```bash
ollama serve &
ollama list  # 检查模型是否存在
ollama pull qwen3-coder:30b  # 拉取模型
```

### Q: 评估大文件时超时？

增加超时时间和 token 上限：
```bash
export EVAL_AGENT_TIMEOUT=300
python3 main.py -f large_file.py --max-tokens 16384
```

### Q: 如何只做静态分析不调 LLM？

**方式一**: Python API
```python
from eval_agent.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer()
result = analyzer.analyze(open("code.py").read(), "code.py")
print(result.code_graph)
print(result.to_dict())
```

**方式二**: Web 界面的「快速扫描」功能，只做 AST 分析不调用 LLM。

### Q: 如何评估非 Python 文件？

直接指定文件即可，语言根据扩展名自动识别：
```bash
python3 main.py -f app.js          # JavaScript
python3 main.py -f main.go         # Go
python3 main.py -f server.rs       # Rust
python3 main.py -f Main.java       # Java
python3 main.py -f deploy.sh       # Shell
```

### Q: 如何清除记忆重新开始？

```bash
rm -rf memory_store/
```

下次运行时会自动重建并初始化默认知识。

### Q: Web 界面无法访问？

1. 确认服务已启动: `python3 main.py --web`
2. 检查端口是否被占用: `lsof -i :8000`
3. 尝试自定义端口: `python3 main.py --web --port 9000`

### Q: 代码片段无法识别语言？

通过 `-c` 参数传入的代码片段默认识别为 Python。如需评估其他语言的代码片段，建议将代码保存为对应扩展名的文件后使用 `-f` 参数。

---

## 11. 版本信息

- 当前版本: **v0.2.0**
- Python 要求: ≥ 3.9
- 依赖: openai ≥ 1.0.0 / fastapi / uvicorn
- 支持语言: 16+ 编程语言
- 记忆系统: 四层架构（工作 / 长期 / 持久 / 外部）
- 默认 LLM: Ollama / qwen3-coder:30b
- 作者: Jiangsheng Yu
- License: MIT
