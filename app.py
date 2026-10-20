"""
项目2：AI智能日程管理助手 -- Streamlit 前端
=============================================
启动：streamlit run app.py
前提：FastAPI 后端必须已经在运行（uvicorn main:app --port 8013）
"""

import os
import streamlit as st
import requests

st.set_page_config(page_title="AI日程助手", page_icon=":calendar:")
st.title("AI 智能日程管理助手")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8013")

st.caption("用自然语言告诉我你的需求，例如：明天下午3点提醒我开会")

# ============================================================
# 聊天输入区
# ============================================================

message = st.text_input(
    "你的需求",
    placeholder="例如：明天下午3点提醒我开会 / 我有哪些任务 / 删掉第一个任务",
)

col1, col2,col3 = st.columns([1, 1,1])
with col1:
    send_button = st.button("发送", type="primary")
with col2:
    view_button = st.button("查看我的任务")
with col3:
    complete_button = st.button("标记完成")

# ============================================================
# 处理发送
# ============================================================

def call_chat(msg: str):
    """调用后端 /chat 接口，返回回复文本"""
    resp = requests.post(f"{API_URL}/chat", json={"message": msg})
    if resp.status_code == 200:
        return resp.json()["reply"]
    else:
        return f"请求失败：{resp.text}"


if send_button and message:
    with st.spinner("AI 正在处理..."):
        try:
            reply = call_chat(message)
            st.markdown("### 回复")
            st.write(reply)
        except requests.exceptions.ConnectionError:
            st.error("无法连接后端，请先启动 FastAPI 服务。")


if view_button:
    with st.spinner("查询中..."):
        try:
            reply = call_chat("我有哪些任务？")
            st.markdown("### 我的任务")
            st.write(reply)
        except requests.exceptions.ConnectionError:
            st.error("无法连接后端，请先启动 FastAPI 服务。")

complete_id = st.text_input("标记完成（输入任务编号）", placeholder="例如：2")
if complete_button and complete_id:
    with st.spinner("标记中..."):
        try:
            reply = call_chat(f"把任务 #{complete_id} 标记为完成")
            st.markdown("### 结果")
            st.write(reply)
        except requests.exceptions.ConnectionError:
            st.error("无法连接后端，请先启动 FastAPI 服务。")


# ============================================================
# 使用说明（初始状态）
# ============================================================

if not message:
    st.divider()
    st.markdown("""
    **使用示例：**
    - `明天下午3点提醒我开会` — 创建任务
    - `我有哪些任务？` — 查看任务列表
    - `删掉第一个任务` — 删除任务
    - `我的第一个任务已完成` — 标记任务已完成
    """)
