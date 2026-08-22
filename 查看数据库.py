"""
查看数据库脚本
================
运行：python 查看数据库.py
作用：把 todo.db 里的所有任务打印出来
"""
import sqlite3

conn = sqlite3.connect("todo.db")
cursor = conn.cursor()

cursor.execute("SELECT id, title, due_time, done FROM tasks ORDER BY id")
rows = cursor.fetchall()
conn.close()

print("=" * 40)
print("当前数据库里的任务：")
print("=" * 40)

if not rows:
    print("  (暂无任务)")
else:
    for r in rows:
        status = "已完成" if r[3] else "未完成"
        print(f"  #{r[0]} | {r[1]} | 时间:{r[2] or '未指定'} | {status}")

print("=" * 40)
print(f"共 {len(rows)} 条任务")
