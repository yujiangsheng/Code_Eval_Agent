"""示例 3: 数据处理管线 — 展示性能优化建议

本文件包含多种性能问题，用于测试 Eval Agent 的性能分析能力:
  - 低效的字符串拼接（循环中使用 +=）
  - 重复计算（未使用缓存）
  - N+1 查询模式
  - 不必要的深拷贝
  - 列表线性查找（应使用集合）

运行评估:
    python3 main.py -f examples/data_processor.py
"""

import copy
import csv
import json
from typing import Optional


class DataProcessor:
    """数据处理管线 — 故意包含多种性能问题"""

    def __init__(self, data: list[dict]):
        self.data = data
        self.processed = []
        self.cache = {}

    def to_csv_string(self) -> str:
        """将数据转为 CSV 字符串

        性能问题 1: 循环中字符串拼接（应使用 join 或 StringIO）
        """
        result = ""
        if not self.data:
            return result
        # 写表头
        headers = list(self.data[0].keys())
        result += ",".join(headers) + "\n"
        # 写数据行 — 每次 += 都创建新字符串对象
        for row in self.data:
            line = ""
            for h in headers:
                line += str(row.get(h, "")) + ","  # 低效拼接
            result += line.rstrip(",") + "\n"
        return result

    def find_duplicates(self) -> list[dict]:
        """查找重复记录

        性能问题 2: O(n²) 的重复检测（应使用哈希/集合）
        """
        duplicates = []
        for i, item1 in enumerate(self.data):
            for j, item2 in enumerate(self.data):
                if i < j and item1 == item2:
                    if item1 not in duplicates:  # list.__contains__ 也是 O(n)
                        duplicates.append(item1)
        return duplicates

    def deep_clone_all(self) -> list[dict]:
        """深拷贝所有数据

        性能问题 3: 不必要的深拷贝（简单字典浅拷贝即可）
        """
        return [copy.deepcopy(item) for item in self.data]

    def fibonacci(self, n: int) -> int:
        """计算斐波那契数

        性能问题 4: 指数级递归（未使用缓存/动态规划）
        """
        if n <= 1:
            return n
        return self.fibonacci(n - 1) + self.fibonacci(n - 2)

    def search_by_name(self, name: str) -> Optional[dict]:
        """按名称搜索记录

        性能问题 5: 每次调用都线性扫描（应构建索引）
        """
        for item in self.data:
            if item.get("name") == name:
                return item
        return None

    def transform_all(self) -> list[dict]:
        """转换所有记录"""
        results = []
        for item in self.data:
            # 每次都重新创建处理函数的闭包（虽然 Python 不严重，但属于不良模式）
            def process(x):
                return {k: str(v).upper() for k, v in x.items()}
            results.append(process(item))
        return results


def load_and_process(filepath: str) -> str:
    """加载 JSON 文件并处理

    综合问题: 缺少错误处理、文件未用 with 保证关闭
    """
    f = open(filepath, "r")  # 未使用 with 语句
    data = json.load(f)
    # f.close() 可能因异常而未执行
    processor = DataProcessor(data)
    return processor.to_csv_string()


if __name__ == "__main__":
    sample_data = [
        {"name": "Alice", "age": 30, "city": "Beijing"},
        {"name": "Bob", "age": 25, "city": "Shanghai"},
        {"name": "Alice", "age": 30, "city": "Beijing"},  # 重复
        {"name": "Charlie", "age": 35, "city": "Guangzhou"},
    ]
    proc = DataProcessor(sample_data)
    print(proc.to_csv_string())
    print("Duplicates:", proc.find_duplicates())
    print("Fibonacci(10):", proc.fibonacci(10))
