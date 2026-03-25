"""示例 1: 基础算法与类 — 用于测试 Eval Agent 的待评估代码

本文件包含若干常见"代码味道"和故意 Bug，展示 Eval Agent 的检测能力:
  - bubble_sort: 经典冒泡排序（无提前终止优化）
  - find_max:    线性查找最大值（缺少空列表保护）
  - Calculator:  简单计算器（缺少除零保护）

运行评估:
    python3 main.py -f examples/sample_code.py
"""


def bubble_sort(arr):
    """冒泡排序 — 时间 O(n²)，未实现提前终止优化"""
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr


def find_max(lst):
    """查找列表最大值 — 缺少空列表边界保护（故意 Bug）"""
    max_val = lst[0]  # 空列表时会抛出 IndexError
    for i in lst:
        if i > max_val:
            max_val = i
    return max_val


class Calculator:
    """简单计算器 — 缺少除零检查（故意 Bug）"""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(('add', a, b, result))
        return result

    def divide(self, a, b):
        # Bug: 未检查 b == 0，会抛出 ZeroDivisionError
        result = a / b
        self.history.append(('divide', a, b, result))
        return result

    def get_history(self):
        return self.history


if __name__ == "__main__":
    print(bubble_sort([64, 34, 25, 12, 22, 11, 90]))
    print(find_max([1, 5, 3, 9, 2]))
    calc = Calculator()
    print(calc.add(1, 2))
    print(calc.divide(10, 0))  # 这里会触发 ZeroDivisionError
