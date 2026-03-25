# Eval Agent

> 面向 Python 与通用代码的**评估与进化型智能体**

基于 LLM（默认本地 Ollama / `qwen3-coder:30b`），集成 AST 静态分析、多维度代码评估、自动修复、改进、测试生成和持续学习能力。

**作者 / 维护者**: Jiangsheng Yu &nbsp;|&nbsp; **License**: MIT

---

## 目录

- [核心能力](#核心能力)
- [架构概览](#架构概览)
- [快速开始](#快速开始)
- [命令行用法](#命令行用法)
- [Python API](#python-api)
- [记忆系统](#记忆系统)
- [输出报告格式](#输出报告格式)
- [配置参考](#配置参考)
- [工作流程详解](#工作流程详解)
- [项目结构](#项目结构)
- [开发指南](#开发指南)

---

## 核心能力

| 模块 | 功能 | 关键类 |
|------|------|--------|
| **静态分析** | AST 解析、Code Graph 构建、McCabe 圈复杂度 | `CodeAnalyzer` |
| **多维评估** | 语法 / 逻辑 / 边界 / 复杂度 / 安全 / 规范 / 可维护性（7 维度） | `Evaluator` |
| **自动修复** | 识别 Bug 并修复，附带原因说明与信心评分 | `Fixer` |
| **代码改进** | 重构 / 性能优化 / 结构优化 / 可读性提升 | `Improver` |
| **测试生成** | 自动生成 pytest 测试用例（正常/边界/异常/性能） | `Validator` |
| **目录扫描** | 递归扫描、跨文件依赖、循环检测、复杂度排行 | `DirectoryScanner` |
| **记忆系统** | 三层记忆架构（工作 → 长期 → 持久知识），持续积累经验 | `WorkingMemory` / `LongTermMemory` / `PersistentKnowledge` |
| **自我校验** | 输出前 LLM 自审，检查遗漏、新 Bug、最佳实践 | `EvalAgent.self_check()` |

---

## 架构概览

```
输入代码/目录
    │
    ▼
┌──────────────────────────────────────────────────────┐
│                    EvalAgent (主编排器)                │
│                                                      │
│  ┌────────────┐  ┌───────────┐  ┌───────────┐       │
│  │ CodeAnalyzer│→│ Evaluator │→│   Fixer   │       │
│  │  (AST分析)  │  │ (7维评估)  │  │ (Bug修复)  │       │
│  └────────────┘  └───────────┘  └─────┬─────┘       │
│                                       │              │
│  ┌────────────┐  ┌───────────┐  ┌─────▼─────┐       │
│  │  Validator │←│ Formatter │←│  Improver │       │
│  │ (测试生成)  │  │ (报告输出)  │  │ (代码改进)  │       │
│  └────────────┘  └───────────┘  └───────────┘       │
│                                                      │
│  ┌───────────────── 记忆系统 ──────────────────┐     │
│  │ WorkingMemory → LongTermMemory → Knowledge │     │
│  └────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
    │
    ▼
  Markdown 报告
```

---

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repo-url> && cd Code_Eval_Agent

# 安装依赖（仅需 openai SDK）
pip install -r requirements.txt

# 确保本地 Ollama 运行中（默认配置）
ollama serve &
ollama pull qwen3-coder:30b
```

### 第一次评估

```bash
# 评估示例文件
python3 main.py -f examples/sample_code.py

# 评估整个项目
python3 main.py -d ./eval_agent -o report.md
```

---

## 命令行用法

```
python3 main.py [选项]
```

### 输入方式（三选一）

| 选项 | 说明 | 示例 |
|------|------|------|
| `-f FILE` | 评估单个文件 | `python3 main.py -f code.py` |
| `-d DIR` | 评估整个目录（递归） | `python3 main.py -d ./src` |
| `-c CODE` | 评估代码片段 | `python3 main.py -c "def f(): pass"` |
| *(管道)* | 从标准输入读取 | `cat code.py \| python3 main.py` |

### 输出选项

| 选项 | 说明 |
|------|------|
| `-o FILE` | 将 Markdown 报告保存到文件 |
| `--self-check` | 启用自我校验（LLM 审核报告质量） |
| `-v` | 详细日志输出（DEBUG 级别） |

### LLM 配置覆盖

| 选项 | 说明 |
|------|------|
| `--api-base URL` | LLM API 端点 |
| `--api-key KEY` | API 密钥 |
| `--model NAME` | 模型名称 |
| `--temperature T` | 采样温度 (0-1) |
| `--max-tokens N` | 最大生成 token 数 |

### 完整示例

```bash
# 使用本地 Ollama（默认配置，无需额外参数）
python3 main.py -f my_script.py

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
```

---

## Python API

```python
from eval_agent import EvalAgent
from config import AgentConfig, LLMConfig

# 使用默认配置（本地 Ollama）
agent = EvalAgent()

# 评估单个文件
with open("my_script.py") as f:
    report = agent.run(f.read(), "my_script.py")
print(report)

# 评估目录
report = agent.run_directory("./src")

# 附加自我校验
report = agent.run_with_check(source_code, "script.py")

# 自定义 LLM 配置
config = AgentConfig(
    llm=LLMConfig(
        api_base="https://api.openai.com/v1",
        api_key="sk-xxx",
        model="gpt-4",
    )
)
agent = EvalAgent(config)
```

---

## 记忆系统

Eval Agent 实现了三层记忆架构，灵感来自认知科学的记忆模型:

| 层级 | 类 | 生命周期 | 内容 |
|------|-----|----------|------|
| **工作记忆** | `WorkingMemory` | 单轮任务 | 当前代码、AST、Code Graph、评估上下文 |
| **长期记忆** | `LongTermMemory` | 跨任务持久化 | Bug 模式、优化策略、代码结构经验 |
| **持久知识** | `PersistentKnowledge` | 永久 | PEP 8 规范、安全清单、常见陷阱 |

### 记忆流转

```
单轮任务开始 → 初始化工作记忆
  → 各步骤写入中间结果
  → 任务结束时提炼经验
  → 写入长期记忆（JSON 持久化）
  → 后续任务检索相关经验
```

长期记忆超出上限（默认 500 条）时，自动按 LRU 策略淘汰（use_count + timestamp 排序）。

---

## 输出报告格式

### 单文件报告（8 章节）

1. **总体评估** — 总分（0-10）与 7 维度评分表
2. **问题清单** — 按严重性分组（🔴严重 / 🟡中等 / 🔵轻微）
3. **代码结构分析** — 行数指标 + Code Graph
4. **修复方案** — 问题修复与原因说明
5. **优化后代码** — 改进后的完整代码
6. **关键改进说明** — 每项改进的类型（🔄重构 / ⚡性能 / 🏗️结构 / 📖可读性）
7. **测试用例** — pytest 代码 + 测试覆盖说明
8. **经验总结** — 提炼并存入长期记忆

### 项目级报告（9 章节）

1. **项目总览** — 规模指标 + 总体评分
2. **架构评估** — 架构模式识别、优势与弱点
3. **项目结构 & Code Graph** — 跨文件依赖可视化
4. **依赖关系分析** — 耦合度、循环依赖、模块依赖图
5. **问题清单** — 语法错误 + 重名冲突 + 安全问题 + 性能隐患
6. **关键文件评估** — Top-5 文件的详细评估
7. **复杂度排行** — 按 McCabe 圈复杂度排序
8. **Top-5 改进建议** — 优先级 + 预期效果 + 投入成本
9. **经验总结**

---

## 配置参考

所有配置项支持环境变量覆盖和命令行参数覆盖:

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `EVAL_AGENT_API_BASE` | LLM API 端点 | `http://localhost:11434/v1` |
| `EVAL_AGENT_API_KEY` | API 密钥 | `ollama` |
| `EVAL_AGENT_MODEL` | 模型名称 | `qwen3-coder:30b` |
| `EVAL_AGENT_TEMPERATURE` | 采样温度 | `0.3` |
| `EVAL_AGENT_MAX_TOKENS` | 最大 token 数 | `8192` |
| `EVAL_AGENT_TIMEOUT` | HTTP 超时（秒） | `120` |
| `EVAL_AGENT_MEMORY_DIR` | 记忆存储目录 | `./memory_store` |

优先级: 命令行参数 > 环境变量 > 默认值

---

## 工作流程详解

### 单文件评估流程

```
Step 1  [AST 解析]   → 提取函数/类/导入/全局变量，计算圈复杂度
Step 2  [Code Graph]  → 生成文本形式的结构图（类/函数/调用关系/复杂度热点）
Step 3  [多维评估]    → LLM 对 7 个维度打分（0-10），输出 issues 列表
Step 4  [问题排序]    → 按严重性排序：严重 > 中等 > 轻微
Step 5  [自动修复]    → 仅当存在"严重"或"中等"问题时触发 LLM 修复
Step 6  [代码改进]    → 在修复后代码上进一步重构/优化/提升可读性
Step 7  [测试生成]    → 为最终代码生成 pytest 测试（正常/边界/异常/性能）
Step 8  [经验总结]    → LLM 提炼本次评估经验，写入长期记忆
Step 9  [格式化输出]  → 汇总为 8 章节 Markdown 报告
```

### 目录评估流程

```
Step 1  [目录扫描]      → 递归发现 .py 文件（过滤 __pycache__/venv 等）
Step 2  [逐文件分析]    → AST 解析 + Code Graph（纯本地，不调用 LLM）
Step 3  [跨文件分析]    → 依赖图 + 循环依赖 + 重名 + 复杂度排行
Step 4  [LLM 深度解读]  → 项目整体架构、质量、安全评估
Step 5  [关键文件评估]  → Top-5 文件逐一 LLM 评估
Step 6  [经验总结]      → 项目级经验写入长期记忆
Step 7  [格式化输出]    → 9 章节 Markdown 报告
```

### 自我校验

使用 `--self-check` 参数时，在输出前额外调用 LLM 检查:
- 是否遗漏了重要问题
- 修复方案是否引入新 Bug
- 建议是否符合 Python 最佳实践
- 是否存在更优解

---

## 项目结构

```
Code_Eval_Agent/
├── main.py                         # CLI 入口
├── config.py                       # 配置（LLM / 记忆 / Agent）
├── requirements.txt                # 依赖：openai>=1.0.0
├── LICENSE                         # MIT License
├── README.md                       # 本文件
├── USAGE.md                        # 详细用法指南
│
├── eval_agent/
│   ├── __init__.py                 # 包入口，导出 EvalAgent
│   ├── agent.py                    # 主编排器（单文件 + 目录两种流程）
│   ├── llm_client.py               # LLM API 客户端（OpenAI 兼容）
│   ├── analyzer.py                 # AST 静态分析 + Code Graph
│   ├── evaluator.py                # 7 维度代码评估
│   ├── fixer.py                    # 自动 Bug 修复
│   ├── improver.py                 # 代码改进
│   ├── validator.py                # pytest 测试生成
│   ├── formatter.py                # Markdown 报告格式化
│   ├── scanner.py                  # 目录扫描 + 跨文件分析
│   └── memory/
│       ├── __init__.py             # 记忆模块入口
│       ├── working_memory.py       # 工作记忆（单轮任务）
│       ├── long_term_memory.py     # 长期记忆（JSON 持久化）
│       └── persistent_knowledge.py # 持久知识库（内置最佳实践）
│
├── examples/
│   ├── sample_code.py              # 基础示例（含故意 Bug）
│   ├── web_handler.py              # Web 处理器示例（安全问题）
│   └── data_processor.py           # 数据处理示例（性能优化）
│
└── memory_store/                   # 记忆持久化目录（自动生成）
    ├── long_term_memory.json
    └── persistent_knowledge.json
```

---

## 开发指南

### 扩展评估维度

在 `evaluator.py` 的 `EVALUATION_SYSTEM_PROMPT` 中添加新维度并更新 JSON schema。

### 添加新知识

```python
from eval_agent.memory import PersistentKnowledge
from config import MemoryConfig

knowledge = PersistentKnowledge(MemoryConfig())
knowledge.add_entry("python_best_practices", "使用 match-case 替代长 if-elif 链（Python 3.10+）")
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

---

## License

MIT License — Copyright (c) 2026 Jiangsheng Yu
