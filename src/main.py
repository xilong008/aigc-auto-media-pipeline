from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import queue
import asyncio
from database import init_db, get_db
import comfyui_client
import rpa_xiaohongshu
import os
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import llm_agent
import os

app = FastAPI(title="AIGC Automation Control Panel")

outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(outputs_dir, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")

# Event for graceful shutdown of SSE
shutdown_event = asyncio.Event()

# --- Logging Emitter for Server-Sent Events (SSE) ---
class LogEmitter:
    def __init__(self):
        self._queues = []

    def log(self, message):
        print(message) 
        for q in self._queues:
            q.put(message)

    def subscribe(self):
        q = queue.Queue()
        self._queues.append(q)
        return q

    def unsubscribe(self, q):
        if q in self._queues:
            self._queues.remove(q)

G_LOGGER = LogEmitter()
# ----------------------------------------------------

class ContentRequest(BaseModel):
    title: str
    body: str
    prompt: str
    engine: str = "comfyui"

class GenerateRequest(BaseModel):
    domain: str = ""
    persona: str = ""
    topic: str = ""

@app.get("/api/stream_logs")
async def stream_logs(request: Request):
    q = G_LOGGER.subscribe()
    async def event_generator():
        try:
            while not shutdown_event.is_set():
                if await request.is_disconnected():
                    break
                try:
                    msg = q.get_nowait()
                    msg = msg.replace('\n', '<br>')
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    await asyncio.sleep(0.2)
        finally:
            G_LOGGER.unsubscribe(q)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.on_event("startup")
def on_startup():
    init_db()

@app.on_event("shutdown")
def on_shutdown():
    shutdown_event.set()

def process_and_publish(task_id: int, request: ContentRequest):
    G_LOGGER.log(f"[RPA Queue] 🚄 任务 #{task_id} 进入后台调度管线... (选用引擎: {request.engine})")
    with get_db() as conn:
        conn.execute("UPDATE content_queue SET status='generating_image' WHERE id=?", (task_id,))
        conn.commit()
    
    # 1. Generate image
    try:
        if request.engine == 'gemini':
            import gemini_client
            img_path = gemini_client.generate_image_from_prompt(request.prompt, logger_cb=G_LOGGER.log)
        elif request.engine == 'siliconflow':
            import siliconflow_client
            img_path = siliconflow_client.generate_image_from_prompt(request.prompt, logger_cb=G_LOGGER.log)
        elif request.engine == 'antigravity':
            G_LOGGER.log(f"[Antigravity] 🛑 任务 #{task_id} 已挂起！请在侧边栏对我说：'帮我为任务 {task_id} 生图'")
            with get_db() as conn:
                conn.execute("UPDATE content_queue SET status='waiting_for_antigravity' WHERE id=?", (task_id,))
                conn.commit()
            return
        else:
            img_path = comfyui_client.generate_image_from_prompt(request.prompt, logger_cb=G_LOGGER.log)
    except Exception as e:
        error_msg = str(e)
        G_LOGGER.log(f"[Generation] 💥 渲染引擎异常: {error_msg}")
        with get_db() as conn:
            conn.execute("UPDATE content_queue SET status='failed', error_message=? WHERE id=?", (error_msg, task_id))
            conn.commit()
        return
    
    if not img_path:
        error_msg = "未输出图像"
        G_LOGGER.log(f"[ComfyUI] ⚠️ 未输出图像，降级取消发布任务。")
        with get_db() as conn:
            conn.execute("UPDATE content_queue SET status='failed', error_message=? WHERE id=?", (error_msg, task_id))
            conn.commit()
        return

    with get_db() as conn:
        conn.execute("UPDATE content_queue SET image_path=?, status='publishing' WHERE id=?", (img_path, task_id))
        conn.commit()
        
    # 2. Publish
    G_LOGGER.log(f"[RPA Engine] 🤖 图像/视频就绪。开始唤醒自动化 RPA 直接发布到小红书...")
    try:
        success = rpa_xiaohongshu.publish_note(request.title, request.body, img_path)
        if success:
            G_LOGGER.log(f"[RPA Engine] ⭐ 已成功发布到小红书！可在笔记管理中查看。")
            with get_db() as conn:
                conn.execute("UPDATE content_queue SET status='done' WHERE id=?", (task_id,))
                conn.commit()
        else:
            raise Exception("RPA执行失败，请检查终端日志")
    except Exception as e:
        error_msg = str(e)
        G_LOGGER.log(f"[RPA Engine] ❌ RPA 执行失败或出错: {error_msg}")
        with get_db() as conn:
            conn.execute("UPDATE content_queue SET status='failed', error_message=? WHERE id=?", (error_msg, task_id))
            conn.commit()

@app.post("/api/schedule_post")
def schedule_post(req: ContentRequest, background_tasks: BackgroundTasks):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO content_queue (title, body, prompt, status) VALUES (?, ?, ?, 'pending')", 
                    (req.title, req.body, req.prompt))
        task_id = cur.lastrowid
        conn.commit()
        
    background_tasks.add_task(process_and_publish, task_id, req)
    return {"message": "Task queued successfully", "task_id": task_id}

@app.get("/api/status")
def get_status(page: int = 1, limit: int = 5):
    offset = (page - 1) * limit
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM content_queue")
        total = cur.fetchone()[0]
        
        cur.execute("SELECT id, title, body, prompt, image_path, status, error_message FROM content_queue ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = cur.fetchall()
        
        result = []
        for r in rows:
            d = dict(r)
            if d.get("image_path"):
                d["image_url"] = "/outputs/" + os.path.basename(d["image_path"])
            result.append(d)
            
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        return {"queue": result, "total": total, "page": page, "total_pages": total_pages}

@app.post("/api/auto_generate")
def manual_trigger_aigc(req: GenerateRequest = GenerateRequest()):
    """
    手动触发 AIGC 流水线 (返回小红书标题、正文、ComfyUI 提示词)
    """
    try:
        from llm_agent import generate_content_payload
        G_LOGGER.log("[System] 👉 收到自动编撰指令，开始初始化智能体队列...")
        result = generate_content_payload(
            domain=req.domain, 
            persona=req.persona, 
            topic_input=req.topic,
            logger_cb=G_LOGGER.log
        )
        G_LOGGER.log("[System] ✅ 任务装配完成，即将返回终端。")
        return {"status": "success", "data": result}
    except Exception as e:
        G_LOGGER.log(f"[System] ❌ 编撰崩溃: {str(e)}")
        return {"status": "error", "detail": str(e)}

import sys
import subprocess

@app.get("/api/account_status")
def get_account_status():
    status = rpa_xiaohongshu.check_login_status()
    return status

@app.post("/api/trigger_login")
def trigger_login():
    try:
        script_path = os.path.join(os.path.dirname(__file__), "login_xhs.py")
        subprocess.Popen([sys.executable, script_path])
        return {"status": "success", "message": "已在系统桌面弹出登录浏览器，请扫码。"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8012, reload=True)
