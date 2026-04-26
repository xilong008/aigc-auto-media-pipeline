import json
import urllib.request
import urllib.parse
import os
import time

COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
WORKFLOW_FILE = os.path.join(os.path.dirname(__file__), "workflow_api.json")

def queue_prompt(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data)
    response = urllib.request.urlopen(req)
    return json.loads(response.read())

def get_history(prompt_id):
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_output_data(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"{COMFYUI_URL}/view?{url_values}") as response:
        return response.read()

def generate_image_from_prompt(text_prompt: str, logger_cb=print):
    logger_cb(f"[ComfyUI] 🎨 开始调度图像/视频渲染引擎...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(WORKFLOW_FILE):
        logger_cb(f"[ComfyUI] ⚠️ 未找到 workflow_api.json。请从 ComfyUI 'Save (API format)' 导出工作流放置于 src 目录下！此次渲染将被跳过。")
        return None
        
    with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
        
    # 自动搜索提示词节点 (寻找 __PROMPT__ 占位符)
    injected_count = 0
    for node_id, node in workflow.items():
        if "inputs" in node and isinstance(node["inputs"], dict):
            for k, v in node["inputs"].items():
                if isinstance(v, str) and "__PROMPT__" in v:
                    node["inputs"][k] = v.replace("__PROMPT__", text_prompt)
                    injected_count += 1
                    
    logger_cb(f"[ComfyUI] ⚙️ 成功注入提示词到 {injected_count} 个输入卡槽。发送任务请求...")
    
    try:
        res = queue_prompt(workflow)
        prompt_id = res['prompt_id']
        logger_cb(f"[ComfyUI] 🕒 任务已加入队列 ID: {prompt_id}，正在等待显卡渲染...")
    except Exception as e:
        logger_cb(f"[ComfyUI] ❌ ComfyUI 调用失败请检查 8188 端口: {e}")
        return None
        
    # Polling history
    while True:
        try:
            history = get_history(prompt_id)
            if prompt_id in history:
                outputs = history[prompt_id]['outputs']
                logger_cb(f"[ComfyUI] ✅ 渲染成功！正在将流媒体文件抓取至本地...")
                for node_id in outputs:
                    node_output = outputs[node_id]
                    # Could be 'images' or 'gifs' or 'videos'
                    for media_type in ['images', 'gifs', 'videos']:
                        if media_type in node_output:
                            for media in node_output[media_type]:
                                file_data = get_output_data(media['filename'], media['subfolder'], media['type'])
                                save_path = os.path.join(OUTPUT_DIR, f"generation_{int(time.time())}_{media['filename']}")
                                with open(save_path, 'wb') as f:
                                    f.write(file_data)
                                logger_cb(f"[ComfyUI] 📁 产物已保存: {save_path}")
                                return save_path
                return None
            time.sleep(2)
        except Exception as e:
            logger_cb(f"[ComfyUI] ⚠️ 轮询断开: {e}")
            time.sleep(2)

