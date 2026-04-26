import os
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/images/generations"

def generate_image_from_prompt(prompt: str, logger_cb=print) -> str:
    """
    Generates an image using SiliconFlow API (Kwai-Kolors/Kolors model) and saves it locally.
    Returns the absolute path to the saved image file.
    """
    if not SILICONFLOW_API_KEY:
        raise ValueError("SILICONFLOW_API_KEY is not set in .env")

    logger_cb(f"[SiliconFlow] 开始调用 Kwai-Kolors/Kolors 免费生图模型...")
    logger_cb(f"[SiliconFlow] Prompt: {prompt[:50]}...")

    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }

    # API Request Body — 注入美感增强关键词
    beauty_suffix = "masterpiece, best quality, ultra-detailed, 8k resolution, cinematic lighting, photorealistic, high saturation, vivid colors, beautiful, aesthetically pleasing, visually stunning, Xiaohongshu style, ins style, elegant composition"
    payload = {
        "model": "Kwai-Kolors/Kolors",
        "prompt": f"{prompt}, {beauty_suffix}",
        "image_size": "960x1280",  # 3:4 ratio is optimal for Xiaohongshu
        "batch_size": 1,
        "num_inference_steps": 30,  # Increase steps for better quality
        "guidance_scale": 7.5
    }

    try:
        start_time = time.time()
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        response_data = response.json()
        if "images" not in response_data or len(response_data["images"]) == 0:
            raise Exception(f"SiliconFlow API returned no images: {response_data}")
            
        image_url = response_data["images"][0]["url"]
        elapsed = time.time() - start_time
        logger_cb(f"[SiliconFlow] 生成成功！耗时: {elapsed:.2f}秒. 正在下载图片...")

        # Download the image
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()

        # Save locally
        output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"siliconflow_{int(time.time())}.png"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(img_response.content)
            
        logger_cb(f"[SiliconFlow] 图片已保存至: {filename}")
        return filepath

    except Exception as e:
        logger_cb(f"[SiliconFlow] 生成或下载失败: {str(e)}")
        raise e

def generate_multiple_images(prompts: list, logger_cb=print) -> list:
    """
    Generates multiple images sequentially using SiliconFlow API.
    Returns a list of absolute paths to the saved image files.
    """
    if not prompts:
        return []
        
    logger_cb(f"[SiliconFlow] 🔄 开始批量生成 {len(prompts)} 张配图...")
    saved_paths = []
    
    for i, prompt in enumerate(prompts):
        logger_cb(f"[SiliconFlow] 🖼️ 正在生成第 {i+1}/{len(prompts)} 张图...")
        try:
            # Add sleep to avoid hitting rate limits if any
            if i > 0:
                time.sleep(2)
            path = generate_image_from_prompt(prompt, logger_cb=logger_cb)
            if path:
                saved_paths.append(path)
        except Exception as e:
            logger_cb(f"[SiliconFlow] ⚠️ 第 {i+1} 张图生成失败: {str(e)}")
            continue
            
    logger_cb(f"[SiliconFlow] ✅ 批量生成结束！成功: {len(saved_paths)}/{len(prompts)}")
    return saved_paths

if __name__ == "__main__":
    # Test script
    print("Testing SiliconFlow Kolors integration...")
    try:
        path = generate_image_from_prompt("一只戴着墨镜的很酷的猫，赛博朋克风格")
        print(f"Success! Image saved at: {path}")
    except Exception as e:
        print(f"Error: {e}")
