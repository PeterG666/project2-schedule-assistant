import sqlite3
import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from mcp import Client, StdioServerParameters


async def main():
    server_path = Path(__file__).resolve().with_name("mcp_server.py")

    with TemporaryDirectory() as folder:
        db_path = Path(folder) / "mcp-test.db"

        params = StdioServerParameters(
            command=sys.executable,
            args=["-B", str(server_path)],
            env={"DB_PATH": str(db_path)},
        )

        async with Client(params) as client:
            result = await client.list_tools()
            print(len(result.tools))
            reply = await client.call_tool("create_task", {"title": "客户端创建测试"})
            print(reply.content[0].text)
            tasks_reply = await client.call_tool("list_tasks", {})
            print(tasks_reply.content[0].text)
            reply_1 = await client.call_tool("create_task", {})
            print(reply_1.content[0].text)
            print(reply_1.is_error)

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT title, done FROM tasks")
            row = cursor.fetchone()
            print(row)
        finally:
            conn.close()


if __name__ == "__main__":
    asyncio.run(main())