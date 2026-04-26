import rpa_xiaohongshu
import os

img_path = "outputs/gemini_1777125839.png"
print(f"Testing with image: {img_path}")
rpa_xiaohongshu.publish_note("测试自动化草稿", "测试草稿内容", img_path)
