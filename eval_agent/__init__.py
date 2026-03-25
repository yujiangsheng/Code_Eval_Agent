"""Eval Agent - 面向 Python 与通用代码的评估与进化型智能体

核心功能：
  - 基于 AST 的静态分析与 Code Graph 构建
  - LLM 驱动的多维度代码评估（语法 / 逻辑 / 边界 / 复杂度 / 安全 / 规范 / 可维护性）
  - 自动 Bug 修复与代码改进（重构 / 性能 / 结构 / 可读性）
  - pytest 测试用例生成
  - 三层记忆系统（工作记忆 → 长期记忆 → 持久知识库）
  - 项目级目录扫描与跨文件依赖分析

快速使用::

    from eval_agent import EvalAgent
    agent = EvalAgent()
    report = agent.run(open('my_script.py').read(), 'my_script.py')
    print(report)

作者: Jiangsheng Yu
License: MIT
"""

from eval_agent.agent import EvalAgent

__all__ = ["EvalAgent"]
__version__ = "0.1.0"
__author__ = "Jiangsheng Yu"
__license__ = "MIT"
