# ⚡ Eval Agent

> **多语言代码评估与进化型智能体** — LLM 驱动的全自动代码质量分析平台

基于 LLM（默认本地 Ollama / `qwen3-coder:30b`），集成 AST 静态分析、7 维度代码评估、自动修复、改进、测试生成和持续学习能力。支持 **16+ 编程语言**。

**作者 / 维护者**: Jiangsheng Yu &nbsp;|&nbsp; **License**: MIT &nbsp;|&nbsp; **版本**: v0.2.0

---

## 目录

- [核心能力](#核心能力)
- [支持的编程语言](#支持的编程语言)
- [架构概览](#架构概览)
- [快速开始](#快速开始)
- [命令行用法](#命令行用法)
- [Web 可视化界面](#web-可视化界面)
- [Python API](#python-api)
- [四层记忆系统](#四层记忆系统)
- [输出报告格式](#输出报告格式)
- [配置参考](#配置参考)
- [工作流程详解](#工作流程详解)
- [项目结构](#项目结构)
- [示例文件](#示例文件)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

---

## 核心能力

| 模块 | 功能 | 关键类 |
|------|------|--------|
| **静态分析** | 多语言 AST/正则解析、Code Graph 构建、McCabe 圈复杂度 | `CodeAnalyzer` |
| **多维评估** | 语法 / 逻辑 / 边界 / 复杂度 / 安全 / 规范 / 可维护性（7 维度） | `Evaluator` |
| **自动修复** | 识别 Bug 并修复，附带原因说明与信心评分（0-10） | `Fixer` |
| **代码改进** | 重构 / 性能优化 / 结构优化 / 可读性提升 | `Improver` |
| **测试生成** | 自动选择测试框架，生成正常/边界/异常/性能四类测试 | `Validator` |
| **目录扫描** | 递归扫描、跨文件依赖、循环检测、复杂度排行 | `DirectoryScanner` |
| **记忆系统** | 四层记忆架构（工作 → 长期 → 持久知识 → 外部），持续积累经验 | `WorkingMemory` / `LongTermMemory` / `PersistentKnowledge` |
| **自我校验** | 输出前 LLM 自审，检查遗漏、新 Bug、最佳实践 | `EvalAgent.self_check()` |
| **Web 界面** | 可视化仪表盘（代码图谱 / 统计图表 / SSE 流式评估） | `web/server.py` |

---

## 支持的编程语言

| 语言 | 分析深度 | 扩展名 |
|------|---------|--------|
| **Python** | ⭐⭐⭐ 深度 AST | `.py` |
| JavaScript / TypeScript | ⭐⭐ 正则模式 | `.js` `.jsx` `.ts` `.tsx` |
| Java | ⭐⭐ 正则模式 | `.java` |
| C / C++ | ⭐⭐ 正则模式 | `.c` `.cpp` `.h` `.hpp` |
| Go | ⭐⭐ 正则模式 | `.go` |
| Rust | ⭐⭐ 正则模式 | `.rs` |
| Ruby | ⭐⭐ 正则模式 | `.rb` |
| PHP | ⭐⭐ 正则模式 | `.php` |
| C# | ⭐⭐ 正则模式 | `.cs` |
| Swift | ⭐⭐ 正则模式 | `.swift` |
| Kotlin | ⭐⭐ 正则模式 | `.kt` `.kts` |
| Scala | ⭐⭐ 正则模式 | `.scala` |
| Lua | ⭐⭐ 正则模式 | `.lua` |
| Shell / Bash | ⭐⭐ 正则模式 | `.sh` `.bash` |
| R | ⭐⭐ 正则模式 | `.r` `.R` |
| Objective-C | ⭐⭐ 正则模式 | `.m` |

> Python 使用 `ast` 模块进行深度语法树分析；其他语言使用针对各语言优化的正则模式提取函数/类/导入等信息。所有语言均可通过 LLM 获得深度评估。

---

## 架构概览

```
输入代码/目录
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│                  EvalAgent (主编排器)                      │
│                                                          │
│  ┌─────────────┐  ┌────────────┐  ┌────────────┐        │
│  │ CodeAnalyzer │→│  Evaluator │→│   Fixer    │        │
│  │ (多语言AST)  │  │ (7维度评估) │  │ (Bug修复)  │        │
│  └─────────────┘  └────────────┘  └─────┬──────┘        │
│                                         │                │
│  ┌─────────────┐  ┌────────────┐  ┌─────▼──────┐        │
│  │  Validator  │←│  Formatter │←│  Improver  │        │
│  │ (测试生成)   │  │ (报告输出)  │  │ (代码改进)  │        │
│  └─────────────┘  └────────────┘  └────────────┘        │
│                                                          │
│  ┌──────────────── 四层记忆系统 ──────────────────┐      │
│  │ Working → LongTerm → Persistent → External    │      │
│  └───────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────┘
    │
    ▼
  Markdown 报告 / Web 可视化仪表盘
```

---

## 快速开始

### 系统要求

- Python ≥ 3.9
- pip
- （可选）[Ollama](https://ollama.ai) — 本地 LLM 推理

### 安装

```bash
# 1. 克隆项目
git clone <repo-url> && cd Code_Eval_Agent

# 2. 安装依赖（仅 3 个包：openai / fastapi / uvicorn）
pip install -r requirements.txt

# 3.（可选）安装并启动 Ollama
ollama serve &
ollama pull qwen3-coder:30b
```

### 第一次评估

```bash
# 评估示例文件（含故意 Bug 的 Python 代码）
python3 main.py -f examples/sample_code.py

# 评估整个项目
python3 main.py -d ./eval_agent -o report.md

# 启动 Web 可视化界面
python3 main.py --web
```

### 验证安装

```bash
python3 main.py --version
# 输出: Eval Agent v0.2.0

python3 main.py --help
```

---

## 命令行用法

```
python3 main.py [选项]
```

### 输入方式（三选一）

| 选项 | 说明 | 示例 |
|------|------|------|
| `-f FILE` | 评估单个文件（支持 16+ 语言） | `python3 main.py -f code.py` |
| `-d DIR` | 评估整个目录（递归扫描） | `python3 main.py -d ./src` |
| `-c CODE` | 评估代码片段 | `python3 main.py -c "def f(): pass"` |
| *(管道)* | 从标准输入读取 | `cat code.py \| python3 main.py` |

### 输出与功能选项

| 选项 | 说明 |
|------|------|
| `-o FILE` | 将 Markdown 报告保存到文件 |
| `--self-check` | 启用自我校验（LLM 审核报告质量） |
| `-v, --verbose` | 详细日志输出（DEBUG 级别） |

### LLM 配置覆盖

| 选项 | 说明 |
|------|------|
| `--api-base URL` | LLM API 端点 |
| `--api-key KEY` | API 密钥 |
| `--model NAME` | 模型名称 |
| `--temperature T` | 采样温度 (0-1) |
| `--max-tokens N` | 最大生成 token 数 |

### Web 界面选项

| 选项 | 说明 |
|------|------|
| `--web` | 启动 Web 可视化界面 |
| `--host ADDR` | 绑定地址（默认 127.0.0.1） |
| `--port PORT` | 绑定端口（默认 8000） |

### 完整示例

```bash
# 使用本地 Ollama（默认配置，无需额外参数）
python3 main.py -f my_script.py

# 评估 JavaScript 文件
python3 main.py -f app.js

# 使用 OpenAI GPT-4
python3 main.py -f code.py \
  --api-base https://api.openai.com/v1 \
  --api-key sk-xxx \
  --model gpt-4

# 项目级评估 + 自我校验 + 详细日志 + 输出文件
python3 main.py -d ./my_project --self-check -v -o report.md

# 代码片段评估
python3 main.py -c "
def fibonacci(n):
    if n <= 1: return n
    return fibonacci(n-1) + fibonacci(n-2)
"

# Web 界面自定义端口
python3 main.py --web --port 9000
```

---

## Web 可视化界面

启动 Web 界面后，在浏览器中访问 `http://127.0.0.1:8000`：

```bash
python3 main.py --web
```

### 功能面板

| 面板 | 说明 |
|------|------|
| **🏠 控制台** | 输入项目路径，执行快速扫描，查看文件统计和问题列表 |
| **🔗 Code Graph** | 交互式代码结构图（文件→类→函数→方法），支持筛选与缩放 |
| **📊 统计分析** | 代码行数分布、文件大小分布、复杂度排行、代码/注释比例 |
| **📝 深度评估** | LLM 驱动的完整评估（SSE 实时进度），支持自定义要求和焦点 |
| **🧠 知识图谱** | 持久知识库的分类展示与交互式图谱可视化 |
| **📚 记忆库** | 四层记忆管理：工作记忆 / 长期记忆 / 持久记忆 / 外部记忆 |

### Web API 端点

```
GET  /                     前端页面
POST /api/scan             快速扫描目录（纯 AST，毫秒级）
POST /api/evaluate         LLM 深度评估（SSE 流式返回）
POST /api/analyze/file     单文件 AST 分析
GET  /api/knowledge        获取持久知识库
GET  /api/memory           获取四层记忆
POST /api/memory/external  添加外部记忆
DEL  /api/memory/external  删除外部记忆
GET  /api/browse           浏览本地目录
POST /api/shutdown         终止服务
```

---

## Python API

### 基础用法

```python
from eval_agent import EvalAgent

agent = EvalAgent()

# 评估单个文件（自动识别语言）
with open("my_script.py") as f:
    report = agent.run(f.read(), "my_script.py")
print(report)

# 评估目录
report = agent.run_directory("./src")

# 附加自我校验
report = agent.run_with_check(source_code, "script.py")
```

### 自定义配置

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
```

### 访问中间结果

```python
agent = EvalAgent()
report = agent.run(source)

# 访问工作记忆中的中间结果
wm = agent.working_memory
print("评估得分:", wm.evaluation.get("overall_score"))
print("问题数:", len(wm.issues))
print("Code Graph:\n", wm.code_graph)
```

### 纯静态分析（不调 LLM）

```python
from eval_agent.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer()
result = analyzer.analyze(open("code.py").read(), "code.py")
print(result.code_graph)         # Code Graph 文本
print(result.to_dict())          # 完整分析数据
```

### 操作记忆系统

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
    "使用 match-case 替代长 if-elif 链（Python 3.10+）")
```

---

## 四层记忆系统

Eval Agent 实现了四层记忆架构，灵感来自认知科学的记忆模型：

| 层级 | 类 / 存储 | 生命周期 | 内容 |
|------|-----------|----------|------|
| **工作记忆** | `WorkingMemory` | 单轮任务 | 当前代码、AST、Code Graph、评估上下文 |
| **长期记忆** | `LongTermMemory` | 跨任务持久化 | Bug 模式、优化策略、代码结构经验 |
| **持久知识** | `PersistentKnowledge` | 永久 | 编码规范、安全清单、常见陷阱（四类内置） |
| **外部记忆** | `external_memory.json` | 永久 | 用户手动添加的笔记与参考上下文 |

### 记忆流转

```
单轮任务开始 → 初始化工作记忆
  → 各步骤写入中间结果
  → 任务结束时提炼经验
  → 写入长期记忆（JSON 持久化）
  → 后续任务检索相关经验
```

长期记忆超出上限（默认 500 条）时，自动按 LRU 策略淘汰（`use_count` + `timestamp` 排序）。

### 持久知识库内置类别

| 类别 | 内容 |
|------|------|
| `python_best_practices` | PEP 8、类型提示、资源管理等 |
| `common_bug_patterns` | 可变默认参数、并发竞态、None 处理等 |
| `optimization_strategies` | 缓存、数据结构选择、异步 I/O 等 |
| `security_checklist` | SQL 注入、XSS、命令注入、SSRF 等 |

---

## 输出报告格式

### 单文件报告（8 章节）

| 章节 | 内容 |
|------|------|
| ① 总体评估 | 总分（0-10）与 7 维度评分表 |
| ② 问题清单 | 按严重性分组（🔴严重 / 🟡中等 / 🔵轻微） |
| ③ 代码结构分析 | 行数指标 + Code Graph |
| ④ 修复方案 | 问题修复与原因说明 |
| ⑤ 优化后代码 | 改进后的完整代码 |
| ⑥ 关键改进说明 | 类型标签（🔄重构 / ⚡性能 / 🏗️结构 / 📖可读性） |
| ⑦ 测试用例 | 自动生成的测试代码 + 覆盖说明 |
| ⑧ 经验总结 | 提炼并存入长期记忆 |

### 项目级报告（9 章节）

| 章节 | 内容 |
|------|------|
| ① 项目总览 | 规模指标 + 总体评分 |
| ② 架构评估 | 架构模式识别、优势与弱点 |
| ③ 项目结构 & Code Graph | 跨文件依赖可视化 |
| ④ 依赖关系分析 | 耦合度、循环依赖、模块依赖图 |
| ⑤ 问题清单 | 语法错误 + 重名冲突 + 安全风险 |
| ⑥ 关键文件评估 | Top-5 文件的详细 LLM 评估 |
| ⑦ 复杂度排行 | 按 McCabe 圈复杂度排序 |
| ⑧ Top-5 改进建议 | 优先级 + 预期效果 + 投入成本 |
| ⑨ 经验总结 | 项目级经验写入长期记忆 |

---

## 配置参考

所有配置项支持环境变量覆盖和命令行参数覆盖。优先级: **命令行参数 > 环境变量 > 默认值**

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `EVAL_AGENT_API_BASE` | LLM API 端点 | `http://localhost:11434/v1` |
| `EVAL_AGENT_API_KEY` | API 密钥 | `ollama` |
| `EVAL_AGENT_MODEL` | 模型名称 | `qwen3-coder:30b` |
| `EVAL_AGENT_TEMPERATURE` | 采样温度 | `0.3` |
| `EVAL_AGENT_MAX_TOKENS` | 最大 token 数 | `8192` |
| `EVAL_AGENT_TIMEOUT` | HTTP 超时（秒） | `120` |
| `EVAL_AGENT_MEMORY_DIR` | 记忆存储目录 | `./memory_store` |

---

## 工作流程详解

### 单文件评估（9 步）

```
Step 1  [语言检测]     → 根据文件扩展名自动识别编程语言
Step 2  [AST 解析]    → 多语言静态分析，提取函数/类/导入/全局变量
Step 3  [Code Graph]   → 生成代码结构图（类/函数/调用关系/复杂度热点）
Step 4  [多维评估]     → LLM 对 7 个维度打分（0-10），输出 issues 列表
Step 5  [问题排序]     → 按严重性排序：严重 > 中等 > 轻微
Step 6  [自动修复]     → 仅当存在"严重"或"中等"问题时触发 LLM 修复
Step 7  [代码改进]     → 在修复后代码上进一步重构/优化/提升可读性
Step 8  [测试生成]     → 根据语言自动选择测试框架，生成四类测试
Step 9  [经验总结]     → LLM 提炼本次评估经验，写入长期记忆
Step 10 [格式化输出]   → 汇总为 8 章节 Markdown 报告
```

### 目录评估（7 步）

```
Step 1  [目录扫描]       → 递归发现代码文件（25+ 扩展名，自动过滤构建目录）
Step 2  [逐文件分析]     → AST/正则解析 + Code Graph（纯本地，不调用 LLM）
Step 3  [跨文件分析]     → 依赖图 + 循环依赖 + 重名检测 + 复杂度排行
Step 4  [LLM 深度解读]   → 项目整体架构、质量、安全评估
Step 5  [关键文件评估]   → Top-5 文件逐一 LLM 评估
Step 6  [经验总结]       → 项目级经验写入长期记忆
Step 7  [格式化输出]     → 9 章节 Markdown 报告
```

### 自我校验

使用 `--self-check` 参数时，在输出前额外调用 LLM 检查:
- 是否遗漏了重要问题
- 修复方案是否引入新 Bug
- 建议是否符合目标语言最佳实践
- 是否存在更优解

---

## 项目结构

```
Code_Eval_Agent/
├── main.py                         # CLI 入口（文件/目录/Web 三种模式）
├── config.py                       # 三层配置（LLM / 记忆 / Agent）
├── requirements.txt                # 依赖：openai / fastapi / uvicorn
├── LICENSE                         # MIT License
├── README.md                       # 本文件
├── USAGE.md                        # 详细用法指南
├── eval_agent_prompt.txt           # Agent 系统提示词
│
├── eval_agent/                     # 核心评估引擎
│   ├── __init__.py                 # 包入口，导出 EvalAgent
│   ├── agent.py                    # 主编排器（单文件 + 目录两种流程）
│   ├── llm_client.py               # LLM API 客户端（OpenAI 兼容）
│   ├── analyzer.py                 # 多语言静态分析 + Code Graph
│   ├── evaluator.py                # 7 维度代码评估
│   ├── fixer.py                    # 自动 Bug 修复
│   ├── improver.py                 # 代码改进（重构/性能/结构/可读性）
│   ├── validator.py                # 测试用例生成
│   ├── formatter.py                # Markdown 报告格式化
│   ├── scanner.py                  # 目录扫描 + 跨文件分析
│   └── memory/                     # 四层记忆系统
│       ├── __init__.py             # 记忆模块入口
│       ├── working_memory.py       # 工作记忆（单轮任务）
│       ├── long_term_memory.py     # 长期记忆（JSON 持久化 + LRU 淘汰）
│       └── persistent_knowledge.py # 持久知识库（四类内置最佳实践）
│
├── web/                            # Web 可视化模块
│   ├── __init__.py                 # Web 模块入口
│   ├── server.py                   # FastAPI 服务端（REST API + SSE）
│   └── static/                     # 前端静态资源
│       ├── index.html              # 主页面（侧边栏 + 6 个面板）
│       ├── app.js                  # 前端交互逻辑
│       └── style.css               # 暗色主题样式
│
├── examples/                       # 示例代码（展示检测能力）
│   ├── sample_code.py              # 算法 Bug（排序/边界/除零）
│   ├── web_handler.py              # 安全漏洞（SQL注入/命令注入/路径遍历）
│   └── data_processor.py           # 性能问题（O(n²)/字符串拼接/无缓存递归）
│
└── memory_store/                   # 记忆持久化目录（自动生成）
    ├── long_term_memory.json       # 长期记忆
    ├── persistent_knowledge.json   # 持久知识库
    └── external_memory.json        # 外部记忆（用户手动添加）
```

---

## 示例文件

项目提供三个精心设计的示例文件，覆盖不同的代码问题场景：

| 文件 | 问题类型 | 检测能力展示 |
|------|---------|-------------|
| `examples/sample_code.py` | 算法 Bug、边界缺失 | 冒泡排序无优化、空列表 IndexError、除零错误 |
| `examples/web_handler.py` | 安全漏洞 | SQL 注入、命令注入、路径遍历、不安全反序列化、硬编码密钥 |
| `examples/data_processor.py` | 性能问题 | O(n²) 重复检测、字符串拼接、无缓存递归、不必要深拷贝 |

```bash
# 逐个评估
python3 main.py -f examples/sample_code.py
python3 main.py -f examples/web_handler.py
python3 main.py -f examples/data_processor.py

# 整体评估
python3 main.py -d examples/ -o examples_report.md
```

---

## 开发指南

### 扩展评估维度

在 `evaluator.py` 的 `EVALUATION_SYSTEM_PROMPT` 中添加新维度并更新 JSON schema。

### 添加新语言支持

在 `analyzer.py` 的 `LANGUAGE_MAP` 中添加映射，并在 `_GENERIC_PATTERNS` 中添加对应的正则模式。

### 添加新知识

```python
from eval_agent.memory import PersistentKnowledge
from config import MemoryConfig

knowledge = PersistentKnowledge(MemoryConfig())
knowledge.add_entry("python_best_practices",
    "使用 match-case 替代长 if-elif 链（Python 3.10+）")
```

### 更换 LLM

```bash
# 环境变量方式
export EVAL_AGENT_API_BASE=https://api.openai.com/v1
export EVAL_AGENT_API_KEY=sk-xxx
export EVAL_AGENT_MODEL=gpt-4o

# 或命令行参数
python3 main.py -f code.py --api-base https://api.openai.com/v1 --model gpt-4o --api-key sk-xxx
```

### 兼容的 LLM 服务

任何兼容 OpenAI Chat Completions API 的服务均可使用：

| 服务 | 示例 |
|------|------|
| **Ollama** (默认) | `--api-base http://localhost:11434/v1` |
| **OpenAI** | `--api-base https://api.openai.com/v1 --api-key sk-xxx` |
| **vLLM** | `--api-base http://localhost:8000/v1` |
| **LiteLLM** | `--api-base http://localhost:4000/v1` |
| **Azure OpenAI** | `--api-base https://YOUR_RESOURCE.openai.azure.com/...` |

---

## 常见问题

<details>
<summary><strong>Q: 遇到 "LLM 调用失败" 错误？</strong></summary>

确保 Ollama 正在运行并且模型已拉取：
```bash
ollama serve &
ollama list           # 检查模型是否存在
ollama pull qwen3-coder:30b
```
</details>

<details>
<summary><strong>Q: 评估大文件时超时？</strong></summary>

```bash
export EVAL_AGENT_TIMEOUT=300
python3 main.py -f large_file.py --max-tokens 16384
```
</details>

<details>
<summary><strong>Q: 如何只做静态分析不调 LLM？</strong></summary>

```python
from eval_agent.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer()
result = analyzer.analyze(open("code.py").read(), "code.py")
print(result.code_graph)
print(result.to_dict())
```

或使用 Web 界面的「快速扫描」功能，只做 AST 分析不调用 LLM。
</details>

<details>
<summary><strong>Q: 记忆文件在哪里？如何清除？</strong></summary>

默认在 `memory_store/` 目录下。清除后重新运行会自动重建并初始化默认知识：
```bash
rm -rf memory_store/
```
</details>

<details>
<summary><strong>Q: 如何评估非 Python 文件？</strong></summary>

直接指定文件即可，语言根据扩展名自动识别：
```bash
python3 main.py -f app.js          # JavaScript
python3 main.py -f main.go         # Go
python3 main.py -f server.rs       # Rust
python3 main.py -f Main.java       # Java
```
</details>

---

## License

MIT License — Copyright (c) 2026 Jiangsheng Yu
