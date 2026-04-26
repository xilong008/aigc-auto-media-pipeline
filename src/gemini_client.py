import os
import json
import base64
import time
import requests
from dotenv import load_dotenv

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")

def generate_image_from_prompt(text_prompt: str, logger_cb=print):
    """
    使用 Google Gemini API (Imagen 3) 生成高质量图片。
    速度极快，适合日常自动化内容运营。
    """
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger_cb("[Gemini API] ❌ 未配置 GEMINI_API_KEY。请在 src/.env 中添加此环境变量！")
        return None
        
    logger_cb(f"[Gemini API] 🎨 开始调度云端图像渲染引擎 (Imagen 4 Fast)...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-fast-generate-001:predict"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    beauty_suffix = "masterpiece, best quality, ultra-detailed, 8k resolution, cinematic lighting, photorealistic, high saturation, vivid colors, beautiful, aesthetically pleasing, visually stunning, Xiaohongshu style, ins style, elegant composition"
    payload = {
        "instances": [
            {
                "prompt": f"{text_prompt}, {beauty_suffix}"
            }
        ],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "3:4"  # 适合小红书比例
        }
    }
    
    try:
        logger_cb(f"[Gemini API] 🚀 正在请求云端集群生图，预计 5-10 秒...")
        response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if "predictions" in data and len(data["predictions"]) > 0:
            b64_img = data["predictions"][0]["bytesBase64Encoded"]
            img_bytes = base64.b64decode(b64_img)
            
            filename = f"gemini_{int(time.time())}.png"
            save_path = os.path.join(OUTPUT_DIR, filename)
            
            with open(save_path, "wb") as f:
                f.write(img_bytes)
                
            logger_cb(f"[Gemini API] ✅ 渲染成功！产物已保存: {save_path}")
            return save_path
        else:
            logger_cb(f"[Gemini API] ⚠️ 接口未返回预测结果: {json.dumps(data)[:200]}")
            return None
            
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                err_data = e.response.json()
                error_msg += f" | {json.dumps(err_data)}"
            except:
                error_msg += f" | {e.response.text[:200]}"
        logger_cb(f"[Gemini API] ❌ API 请求失败: {error_msg}")
        return None

def generate_multiple_images(prompts: list, logger_cb=print) -> list:
    """
    Generates multiple images sequentially using Gemini API.
    Returns a list of absolute paths to the saved image files.
    """
    if not prompts:
        return []
        
    logger_cb(f"[Gemini API] 🔄 开始批量生成 {len(prompts)} 张配图...")
    saved_paths = []
    
    for i, prompt in enumerate(prompts):
        logger_cb(f"[Gemini API] 🖼️ 正在生成第 {i+1}/{len(prompts)} 张图...")
        try:
            # Add small sleep to avoid hitting rate limits
            if i > 0:
                time.sleep(2)
            path = generate_image_from_prompt(prompt, logger_cb=logger_cb)
            if path:
                saved_paths.append(path)
        except Exception as e:
            logger_cb(f"[Gemini API] ⚠️ 第 {i+1} 张图生成失败: {str(e)}")
            continue
            
    logger_cb(f"[Gemini API] ✅ 批量生成结束！成功: {len(saved_paths)}/{len(prompts)}")
    return saved_paths
