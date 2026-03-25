"""示例 2: Web 请求处理器 — 展示安全问题检测

本文件包含多种常见安全漏洞，用于测试 Eval Agent 的安全审计能力:
  - SQL 注入（字符串拼接构建 SQL）
  - 命令注入（os.system 执行用户输入）
  - 路径遍历（未验证文件路径）
  - 硬编码密钥
  - 不安全的反序列化（pickle）

运行评估:
    python3 main.py -f examples/web_handler.py
"""

import os
import pickle
import sqlite3


# 安全问题 1: 硬编码密钥
SECRET_KEY = "my-super-secret-key-12345"
DATABASE_URL = "sqlite:///app.db"


class UserHandler:
    """用户请求处理器 — 故意包含多种安全漏洞"""

    def __init__(self, db_path="app.db"):
        self.db_path = db_path

    def get_user(self, username: str) -> dict:
        """根据用户名查询用户信息

        安全问题 2: SQL 注入 — 使用字符串拼接而非参数化查询
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 危险: 直接拼接用户输入到 SQL 语句
        query = f"SELECT * FROM users WHERE username = '{username}'"
        cursor.execute(query)
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2]}
        return {}

    def run_diagnostic(self, command: str) -> str:
        """执行系统诊断命令

        安全问题 3: 命令注入 — 使用 os.system 执行用户输入
        """
        # 危险: 直接执行用户提供的命令
        result = os.popen(command).read()
        return result

    def read_file(self, filename: str) -> str:
        """读取用户请求的文件

        安全问题 4: 路径遍历 — 未验证文件路径
        """
        # 危险: 用户可通过 ../../etc/passwd 访问任意文件
        filepath = os.path.join("/data/uploads", filename)
        with open(filepath, "r") as f:
            return f.read()

    def load_session(self, session_data: bytes) -> dict:
        """加载会话数据

        安全问题 5: 不安全反序列化
        """
        # 危险: pickle.loads 可执行任意代码
        return pickle.loads(session_data)

    def authenticate(self, token: str) -> bool:
        """验证用户 token"""
        return token == SECRET_KEY


if __name__ == "__main__":
    handler = UserHandler()
    # 正常用法
    print(handler.authenticate("test-token"))
