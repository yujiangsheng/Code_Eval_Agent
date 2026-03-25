"""长期记忆 — 跨任务的经验积累与检索

以 JSON 文件持久化存储，支持按关键词 / 类别检索。
超出容量上限时自动按 LRU（use_count + timestamp）策略淘汰。

存储格式（每条记录）::

    {
      "category":    "bug_pattern | optimization | structure | general",
      "content":     "经验描述文本",
      "tags":        ["标签1", "标签2"],
      "source_file": "来源文件名",
      "timestamp":   "ISO 时间戳",
      "use_count":   被检索引用次数
    }
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

from config import MemoryConfig

logger = logging.getLogger(__name__)


class LongTermMemory:
    """长期记忆：存储跨任务的经验

    内容包括：
    - 常见 Bug 模式
    - 优化策略
    - 代码结构经验

    以 JSON 文件持久化存储。
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._store_path = os.path.join(config.memory_dir, config.long_term_file)
        self._entries: list[dict] = []
        self._load()

    def _ensure_dir(self):
        os.makedirs(self.config.memory_dir, exist_ok=True)

    def _load(self):
        """从文件加载长期记忆"""
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    self._entries = json.load(f)
                logger.info("加载了 %d 条长期记忆", len(self._entries))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("加载长期记忆失败: %s", e)
                self._entries = []
        else:
            self._entries = []

    def _save(self):
        """持久化到文件"""
        self._ensure_dir()
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2)

    def add(
        self,
        category: str,
        content: str,
        tags: Optional[list[str]] = None,
        source_file: Optional[str] = None,
    ):
        """添加一条经验记录

        Args:
            category: 类别 (bug_pattern / optimization / structure / general)
            content: 经验内容
            tags: 标签列表
            source_file: 来源文件名
        """
        entry = {
            "category": category,
            "content": content,
            "tags": tags or [],
            "source_file": source_file or "",
            "timestamp": datetime.now().isoformat(),
            "use_count": 0,
        }
        self._entries.append(entry)

        # 超出上限时移除最早且使用次数最少的条目
        if len(self._entries) > self.config.max_long_term_entries:
            self._entries.sort(key=lambda e: (e.get("use_count", 0), e["timestamp"]))
            self._entries = self._entries[1:]

        self._save()
        logger.debug("新增长期记忆: [%s] %s", category, content[:80])

    def search(
        self,
        keywords: Optional[list[str]] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """搜索相关经验

        Args:
            keywords: 关键词列表（任意匹配）
            category: 过滤类别
            limit: 返回数量上限
        """
        results = self._entries
        if category:
            results = [e for e in results if e["category"] == category]
        if keywords:
            kw_lower = [k.lower() for k in keywords]
            results = [
                e
                for e in results
                if any(
                    kw in e["content"].lower() or kw in " ".join(e.get("tags", [])).lower()
                    for kw in kw_lower
                )
            ]
        # 按使用次数和时间排序
        results.sort(key=lambda e: (e.get("use_count", 0), e["timestamp"]), reverse=True)
        limit = limit or self.config.max_relevant_memories
        return results[:limit]

    def increment_use(self, entry: dict):
        """记录一次使用"""
        for e in self._entries:
            if e["timestamp"] == entry["timestamp"] and e["content"] == entry["content"]:
                e["use_count"] = e.get("use_count", 0) + 1
                self._save()
                return

    def format_for_prompt(self, entries: list[dict]) -> str:
        """将记忆条目格式化为可嵌入 prompt 的文本"""
        if not entries:
            return "（暂无相关历史经验）"
        lines = []
        for i, e in enumerate(entries, 1):
            lines.append(f"{i}. [{e['category']}] {e['content']}")
            if e.get("tags"):
                lines.append(f"   标签: {', '.join(e['tags'])}")
        return "\n".join(lines)

    @property
    def size(self) -> int:
        return len(self._entries)
