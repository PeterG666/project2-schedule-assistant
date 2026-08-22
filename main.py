"""
项目2：AI智能日程管理助手
==========================
让 AI 理解用户意图，自主决定调用哪个工具来管理日程。

架构：
  用户说话 → FastAPI /chat → LangGraph Agent
           → AI 判断意图 → 调用 create_task / list_tasks / delete_task
           → 工具写 SQLite → AI 用自然语言回复

启动：
  source venv/Scripts/activate
  export DEEPSEEK_API_KEY="sk-你的Key"
  uvicorn main:app --port 8013

测试：http://127.0.0.1:8013/docs 的 POST /chat
"""

import os, json, sqlite3
from typing import Annotated, Literal, TypedDict
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage

API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_BASE = "https://api.deepseek.com"
DB_PATH = "todo.db"

app = FastAPI(title="AI日程管理助手")

# ============================================================
# 第 1 块：SQLite 数据库初始化
# ============================================================

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

init_db()   # 启动时建表


# ============================================================
# 第 2 块：三个工具函数（Agent 能调用的"外部能力"）
# ============================================================

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
    
        

# 工具名 → 实际函数 的映射
TOOL_MAP = {
    "create_task": create_task,
    "list_tasks": list_tasks,
    "delete_task": delete_task,
    "complete_task":complete_task,
}


# ============================================================
# 第 3 块：工具的"说明书"（给 LLM 看的）
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "创建一个新任务/提醒。当用户说'提醒我'、'记一下'、'添加任务'等时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "任务内容，如'开会'"},
                    "due_time": {"type": "string", "description": "时间，如'明天下午3点'，可为空"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "查看所有任务。当用户问'我有哪些任务'、'看看我的日程'时调用。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "删除一个任务。当用户说'删掉'、'取消'某个任务时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "要删除的任务 id"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "标记一个任务为已完成。当用户说'完成'、'做完了'、'搞定'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "任务序号，如'任务1'。"}
                },
                "required": ["task_id"]
            }
        }
    },
]


# ============================================================
# 第 4 块：LangGraph Agent（复用 Day 10 的结构）
# ============================================================

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


llm = ChatOpenAI(model="deepseek-chat", api_key=API_KEY, base_url=API_BASE, temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)


def llm_node(state: AgentState) -> AgentState:
    """LLM 决策节点"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def tool_node(state: AgentState) -> AgentState:
    """工具执行节点"""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    result_messages = []
    for tc in tool_calls:
        tool_name = tc["name"]
        raw_args = tc["args"]
        tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        print(f"[工具调用] {tool_name}({tool_args})")

        func = TOOL_MAP[tool_name]
        result = func(**tool_args)
        print(f"[工具结果] {result}")

        result_messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    return {"messages": result_messages}


def router(state: AgentState) -> Literal["tool_node", "__end__"]:
    """判断走工具还是结束"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
    return "__end__"


def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("llm", llm_node)
    graph.add_node("tool_node", tool_node)
    graph.set_entry_point("llm")
    graph.add_conditional_edges("llm", router)
    graph.add_edge("tool_node", "llm")
    return graph.compile()


agent = build_agent()


# ============================================================
# 第 5 块：FastAPI 接口
# ============================================================

class ChatRequest(BaseModel):
    message: str


SYSTEM_PROMPT = (
    "你是一个日程管理助手。用户用自然语言告诉你他的需求，"
    "你需要判断该调用哪个工具（创建任务/查看任务/删除任务），"
    "执行后用中文简洁地回复用户。"
)


@app.get("/")
def root():
    return {"message": "AI日程管理助手已就绪，POST /chat 来对话吧。"}


@app.post("/chat")
def chat(req: ChatRequest):
    """自然语言交互入口"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=req.message),
    ]

    result = agent.invoke({"messages": messages})

    # 取最后一条消息作为回复
    final = result["messages"][-1]
    reply = final.content if hasattr(final, "content") else str(final)

    return {"reply": reply}
