"""持久知识库 — 编程最佳实践、常见陷阱与安全清单

本模块提供四类内置知识:
  - python_best_practices:  PEP 8、类型提示、资源管理等
  - common_bug_patterns:    可变默认参数、并发竞态、None 处理等
  - optimization_strategies: 缓存、数据结构选择、异步 I/O 等
  - security_checklist:     SQL 注入、XSS、命令注入等

知识库首次创建时自动写入默认条目，后续可通过 add_entry() 扩展。
Agent 在改进阶段会调用 get_relevant() 检索相关知识嵌入 prompt。
"""

from __future__ import annotations

import json
import logging
import os

from config import MemoryConfig

logger = logging.getLogger(__name__)

# 内置默认知识
_DEFAULT_KNOWLEDGE = {
    "python_best_practices": [
        "遵循 PEP 8 编码规范",
        "使用类型提示（Type Hints）提升可读性",
        "优先使用列表推导式替代简单循环",
        "使用 with 语句管理资源",
        "避免可变默认参数（如 def f(x=[])）",
        "使用 logging 而非 print 进行调试",
        "异常处理应捕获具体异常类型，避免裸 except",
        "使用 pathlib 替代 os.path 进行路径操作",
        "大数据量时优先使用生成器而非列表",
        "使用 dataclass 或 NamedTuple 替代普通字典存储结构化数据",
    ],
    "common_bug_patterns": [
        "可变默认参数导致状态泄漏",
        "循环中修改正在迭代的列表",
        "忘记关闭文件/连接（应用 with 语句）",
        "整数溢出（Python 无此问题，但跨语言注意）",
        "浮点数精度比较（应使用 math.isclose）",
        "递归深度溢出（需检查递归终止条件）",
        "字符串拼接性能问题（大量拼接用 join）",
        "全局变量污染",
        "未处理的 None 值",
        "并发竞态条件",
    ],
    "optimization_strategies": [
        "时间换空间 / 空间换时间的权衡",
        "使用合适的数据结构（dict 查找 O(1) vs list O(n)）",
        "缓存重复计算（functools.lru_cache）",
        "避免不必要的深拷贝",
        "使用内置函数替代手写循环（map, filter, sum 等）",
        "数据库查询优化：避免 N+1 查询",
        "I/O 密集型任务使用异步",
        "CPU 密集型任务使用多进程",
    ],
    "security_checklist": [
        "SQL 注入：使用参数化查询",
        "XSS：对用户输入进行转义",
        "命令注入：避免 os.system，使用 subprocess 并禁用 shell=True",
        "路径遍历：验证文件路径",
        "敏感信息：不要硬编码密钥/密码",
        "反序列化：避免 pickle.loads 处理不可信数据",
        "SSRF：验证外部 URL",
        "依赖安全：定期检查已知漏洞",
    ],
}


class PersistentKnowledge:
    """持久知识库

    包含固化的编程最佳实践、框架经验和标准库使用模式。
    支持用户自定义扩展。
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._store_path = os.path.join(config.memory_dir, config.knowledge_file)
        self._knowledge: dict = {}
        self._load()

    def _ensure_dir(self):
        os.makedirs(self.config.memory_dir, exist_ok=True)

    def _load(self):
        """加载知识库，不存在则使用默认知识初始化"""
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    self._knowledge = json.load(f)
                logger.info("加载知识库: %d 个类别", len(self._knowledge))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("加载知识库失败: %s, 使用默认知识", e)
                self._knowledge = dict(_DEFAULT_KNOWLEDGE)
                self._save()
        else:
            self._knowledge = dict(_DEFAULT_KNOWLEDGE)
            self._save()

    def _save(self):
        self._ensure_dir()
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(self._knowledge, f, ensure_ascii=False, indent=2)

    def get_category(self, category: str) -> list[str]:
        """获取指定类别的知识条目"""
        return self._knowledge.get(category, [])

    def add_entry(self, category: str, entry: str):
        """向指定类别添加知识条目"""
        if category not in self._knowledge:
            self._knowledge[category] = []
        if entry not in self._knowledge[category]:
            self._knowledge[category].append(entry)
            self._save()

    def get_relevant(self, keywords: list[str]) -> str:
        """根据关键词获取相关知识，格式化为 prompt 可用文本"""
        kw_lower = [k.lower() for k in keywords]
        relevant = []
        for cat, entries in self._knowledge.items():
            matched = [
                e for e in entries if any(kw in e.lower() for kw in kw_lower)
            ]
            if matched:
                relevant.append(f"【{cat}】")
                for e in matched:
                    relevant.append(f"  - {e}")
        return "\n".join(relevant) if relevant else "（暂无匹配的知识条目）"

    def format_all(self) -> str:
        """格式化全部知识"""
        lines = []
        for cat, entries in self._knowledge.items():
            lines.append(f"【{cat}】")
            for e in entries:
                lines.append(f"  - {e}")
        return "\n".join(lines)

    @property
    def categories(self) -> list[str]:
        return list(self._knowledge.keys())
