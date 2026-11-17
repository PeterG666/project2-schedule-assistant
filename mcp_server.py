import task_service
from mcp.server import MCPServer

server=MCPServer('Schedule Assistant')

@server.tool()
def list_tasks() -> str:
    """列出所有日程任务及其完成状态"""
    return task_service.list_tasks()

@server.tool()
def create_task(title: str, due_time: str = "") -> str:
    """创建任务"""
    return task_service.create_task(title,due_time)

@server.tool()
def delete_task(task_id: int) -> str:
    """删除任务"""
    return task_service.delete_task(task_id)

@server.tool()
def complete_task(task_id: int) ->str:
    """标记完成任务"""
    return task_service.complete_task(task_id)

if __name__ == "__main__":
    task_service.init_db()
    server.run(transport="stdio")