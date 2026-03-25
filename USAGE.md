# Eval Agent 详细用法指南

本文档提供 Eval Agent 的详细用法说明、高级配置与常见问题解答。

---

## 1. 安装与环境准备

### 前置条件

- Python 3.9+
- pip
- （可选）Ollama — 用于本地 LLM 推理

### 安装步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd Code_Eval_Agent

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3.（可选）安装并启动 Ollama
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
ollama pull qwen3-coder:30b
```

### 验证安装

```bash
python3 main.py --version
# 输出: Eval Agent v0.1.0

python3 main.py --help
```

---

## 2. 基础使用

### 2.1 评估单个文件

```bash
python3 main.py -f examples/sample_code.py
```

输出为 8 章节 Markdown 报告，包含评分、问题清单、修复方案、改进代码和测试用例。

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

输出 9 章节项目级报告，包含架构评估、依赖分析、复杂度排行和 Top-5 改进建议。

### 2.5 保存报告到文件

```bash
python3 main.py -f code.py -o report.md
python3 main.py -d ./src -o project_report.md
```

---

## 3. 高级功能

### 3.1 自我校验模式

```bash
python3 main.py -f code.py --self-check
```

在生成报告后，额外调用 LLM 审核报告质量，检查：
- 是否遗漏了重要问题
- 修复方案是否引入新 Bug
- 建议是否符合最佳实践
- 是否存在更优解

### 3.2 详细日志

```bash
python3 main.py -f code.py -v
```

启用 DEBUG 级别日志，输出每个步骤的详细过程，包括 LLM 调用信息。

### 3.3 组合使用

```bash
# 完整组合: 目录评估 + 自我校验 + 详细日志 + 输出文件
python3 main.py -d ./my_project --self-check -v -o full_report.md
```

---

## 4. LLM 配置

### 4.1 使用本地 Ollama（默认）

无需额外配置，确保 Ollama 运行并已拉取模型即可：

```bash
ollama serve &
ollama pull qwen3-coder:30b
python3 main.py -f code.py
```

### 4.2 使用 OpenAI

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

### 4.3 使用其他兼容服务

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

### 4.4 调节生成参数

```bash
# 降低温度获得更确定的输出
python3 main.py -f code.py --temperature 0.1

# 增加 token 上限以处理大文件
python3 main.py -f code.py --max-tokens 16384
```

---

## 5. Python API 使用

### 5.1 基础用法

```python
from eval_agent import EvalAgent

agent = EvalAgent()

# 评估源代码字符串
source = open("my_script.py").read()
report = agent.run(source, "my_script.py")
print(report)
```

### 5.2 目录评估

```python
report = agent.run_directory("./src")
print(report)
```

### 5.3 自定义配置

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

### 5.4 访问中间结果

```python
agent = EvalAgent()
report = agent.run(source)

# 访问工作记忆中的中间结果
wm = agent.working_memory
print("评估得分:", wm.evaluation.get("overall_score"))
print("问题数:", len(wm.issues))
print("Code Graph:\n", wm.code_graph)
```

### 5.5 操作记忆系统

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

## 6. 示例文件

项目提供三个示例文件，覆盖不同的代码问题场景:

| 文件 | 问题类型 | 评估命令 |
|------|---------|---------|
| `examples/sample_code.py` | 算法 Bug、边界问题 | `python3 main.py -f examples/sample_code.py` |
| `examples/web_handler.py` | 安全漏洞（SQL注入、命令注入等） | `python3 main.py -f examples/web_handler.py` |
| `examples/data_processor.py` | 性能问题（O(n²)、字符串拼接等） | `python3 main.py -f examples/data_processor.py` |

### 评估整个 examples 目录

```bash
python3 main.py -d examples/ -o examples_report.md
```

---

## 7. 常见问题

### Q: 遇到 "LLM 调用失败" 错误？

确保 Ollama 正在运行并且模型已拉取：
```bash
ollama serve &
ollama list  # 检查模型是否存在
ollama pull qwen3-coder:30b  # 拉取模型
```

### Q: 评估大文件时超时？

增加超时时间：
```bash
export EVAL_AGENT_TIMEOUT=300  # 秒
python3 main.py -f large_file.py
```

或增加 max_tokens：
```bash
python3 main.py -f large_file.py --max-tokens 16384
```

### Q: 如何只做静态分析不调 LLM？

目前 CLI 不直接支持，但可通过 Python API：
```python
from eval_agent.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer()
result = analyzer.analyze(open("code.py").read(), "code.py")
print(result.code_graph)
print(result.to_dict())
```

### Q: 记忆文件在哪里？

默认在项目根目录的 `memory_store/` 下：
```
memory_store/
├── long_term_memory.json      # 长期记忆
└── persistent_knowledge.json  # 知识库
```

可通过 `EVAL_AGENT_MEMORY_DIR` 或 `--memory-dir` 自定义路径。

### Q: 如何清除记忆重新开始？

```bash
rm -rf memory_store/
```

下次运行时会自动重建并初始化默认知识。

---

## 8. 版本信息

- 当前版本: v0.1.0
- Python 要求: ≥ 3.9
- 依赖: openai ≥ 1.0.0
- 默认 LLM: Ollama / qwen3-coder:30b
- 作者: Jiangsheng Yu
- License: MIT
