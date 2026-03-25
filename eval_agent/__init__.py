"""Eval Agent — 面向多语言代码的评估与进化型智能体

核心能力:
  - **多语言静态分析**: Python 深度 AST 分析 + 其他语言正则分析
  - **LLM 7 维度评估**: 语法 / 逻辑 / 边界 / 复杂度 / 安全 / 规范 / 可维护性
  - **自动 Bug 修复**: 附带修复原因说明与信心评分
  - **代码改进**: 重构 / 性能 / 结构 / 可读性提升
  - **测试生成**: 根据语言自动选择测试框架
  - **四层记忆系统**: 工作记忆 → 长期记忆 → 持久知识 → 外部记忆
  - **项目级目录扫描**: 跨文件依赖 + 循环检测 + 复杂度排行

支持的语言:
  Python, JavaScript/TypeScript, Java, C/C++, Go, Rust, Ruby, PHP,
  C#, Swift, Kotlin, Scala, Lua, Shell/Bash, R, Objective-C 等 16+

快速使用::

    from eval_agent import EvalAgent

    # 单文件评估
    agent = EvalAgent()
    report = agent.run(open('my_script.py').read(), 'my_script.py')
    print(report)

    # 目录评估
    report = agent.run_directory('./src')

    # 自我校验
    report = agent.run_with_check(source, 'script.py')

作者: Jiangsheng Yu
License: MIT
"""

from eval_agent.agent import EvalAgent

__all__ = ["EvalAgent"]
__version__ = "0.2.0"
__author__ = "Jiangsheng Yu"
__license__ = "MIT"
