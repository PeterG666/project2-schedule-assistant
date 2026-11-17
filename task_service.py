import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "todo.db")
def init_db():
    """创建数据库和表（如果不存在）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_time TEXT,
            done INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def create_task(title: str, due_time: str = "") -> str:
    """创建一条任务"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, due_time) VALUES (?, ?)",
        (title, due_time)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return f"已创建任务 #{task_id}：{title}（时间：{due_time or '未指定'}）"

def list_tasks() -> str:
    """列出所有未完成的任务"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, due_time, done FROM tasks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "目前没有任何任务。"

    result = []
    for r in rows:
        status = "✅已完成" if r[3] else "⏳未完成"
        result.append(f"#{r[0]} {r[1]}（{r[2] or '无时间'}）{status}")
    return "\n".join(result)

def delete_task(task_id: int) -> str:
    """按 id 删除一条任务"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted == 0:
        return f"任务 #{task_id} 不存在。"
    return f"已删除任务 #{task_id}。"

def complete_task(task_id: int) ->str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET done = 1 WHERE id = ?",(task_id,))
    conn.commit()
    completed = cursor.rowcount
    conn.close()
    if not completed:
        return "任务不存在"
    return f"已标记任务 #{task_id}完成。"
