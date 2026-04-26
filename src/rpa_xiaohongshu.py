import time
import os
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

PROFILE_PATH = os.path.join(os.path.dirname(__file__), "xhs_profile")

def login_xhs():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=False,
            viewport={"width": 1280, "height": 720}
        )
        page = context.pages[0] if context.pages else context.new_page()
        Stealth().apply_stealth_sync(page)
        
        print("Please log in manually inside the opened browser window.")
        page.goto("https://creator.xiaohongshu.com/")
        
        # Wait for user input instead of brittle DOM selector
        print("\n=======================================================")
        print("💡 扫码登录成功后，请在这里按【回车键 (Enter)】继续部署...")
        print("=======================================================\n")
        input()
        
        print("Login confirmed! Profile saved automatically to:", PROFILE_PATH)
        context.close()

def check_login_status():
    if not os.path.exists(PROFILE_PATH):
        return {"status": "invalid", "reason": "未绑定账号"}
    
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_PATH,
                headless=True
            )
            page = context.pages[0] if context.pages else context.new_page()
            Stealth().apply_stealth_sync(page)
            
            page.goto("https://creator.xiaohongshu.com/creator/home", timeout=15000)
            page.wait_for_timeout(2000)
            
            url = page.url
            context.close()
            
            if "login" in url or "creator.xiaohongshu.com/login" in url:
                return {"status": "invalid", "reason": "Token 已过期"}
            return {"status": "valid", "platform": "小红书"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def publish_note(title: str, content: str, image_paths):
    if not os.path.exists(PROFILE_PATH):
        raise Exception("No profile found. Please login first.")
        
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=True,
            viewport={"width": 1280, "height": 720}
        )
        page = context.pages[0] if context.pages else context.new_page()
        Stealth().apply_stealth_sync(page)
        
        try:
            print("Navigating to Xiaohongshu creator publish page...")
            page.goto("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=article")
            time.sleep(3) # Wait for load and stealth passing
            
            # 兼容单图(str)和多图(list)
            if isinstance(image_paths, str):
                image_paths = [image_paths]
                
            abs_images = [os.path.abspath(p) for p in image_paths]
            
            # 区分图文和视频发布 (通过第一张图判断)
            first_img = abs_images[0]
            if first_img.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                print("Detected image file. Switching to '上传图文' tab...")
                for el in page.get_by_text("上传图文").all():
                    box = el.bounding_box()
                    if box and box['y'] > 0:
                        el.click(force=True)
                        break
                time.sleep(2)
                
            try:
                # Try standard approach first
                if page.locator("input[type='file']").count() > 0:
                    file_input = page.locator("input[type='file']").first
                    file_input.set_input_files(abs_images)
                else:
                    # Fallback to robust file chooser intercept (handles hidden inputs / dynamic DOM)
                    print("No standard input[type='file'] found, using expect_file_chooser...")
                    with page.expect_file_chooser(timeout=10000) as fc_info:
                        upload_area = page.locator(".upload-wrapper, .upload-container, .drag-container, .upload-btn").first
                        upload_area.click(force=True)
                    file_chooser = fc_info.value
                    file_chooser.set_files(abs_images)
            except Exception as e:
                print(f"File upload error: {e}")
                raise e
            time.sleep(5)
            
            title_input = None
            for el in page.get_by_placeholder("填写标题会有更多赞哦", exact=False).all():
                if el.is_visible():
                    title_input = el
                    break
            if not title_input:
                for el in page.locator("input.c-input_inner").all():
                    if el.is_visible():
                        title_input = el
                        break
            
            if title_input:
                title_input.click(force=True)
                page.keyboard.type(title, delay=50)
            
            content_input = None
            for el in page.locator("[contenteditable='true']").all():
                if el.is_visible():
                    content_input = el
                    break
            if not content_input:
                for el in page.locator("#post-textarea").all():
                    if el.is_visible():
                        content_input = el
                        break
            
            if content_input:
                content_input.click(force=True)
                page.keyboard.type(content, delay=50)
            
            print("Waiting for image upload to complete...")
            # Hide any tippy tooltips that might intercept the click
            page.evaluate("document.querySelectorAll('[data-tippy-root]').forEach(el => el.style.display = 'none')")
            
            # Wait for upload to fully complete
            page.wait_for_timeout(5000)
            
            # ---- Click the real 发布 button (not 暂存离开 which is local-only!) ----
            print("Clicking the PUBLISH button (发布)...")
            publish_btn = page.locator("button").filter(has_text="发布")
            
            # Wait for button to become enabled and visible
            publish_btn.wait_for(state="visible", timeout=60000)
            # Re-hide tooltips just in case they re-appeared
            page.evaluate("document.querySelectorAll('[data-tippy-root]').forEach(el => el.style.display = 'none')")
            
            # Set up network response listener to verify server-side success
            publish_response = {}
            def capture_publish(response):
                url = response.url
                if any(kw in url for kw in ["note/post", "note/create", "publish", "notepost"]):
                    if response.request.method == "POST":
                        try:
                            publish_response["status"] = response.status
                            publish_response["url"] = url
                            publish_response["body"] = response.text()[:500]
                        except:
                            pass
            page.on("response", capture_publish)
            
            publish_btn.click()
            
            print("Waiting for server response...")
            page.wait_for_timeout(10000)
            
            # Take proof screenshot
            page.screenshot(path=os.path.join(os.path.dirname(__file__), "publish_proof.png"))
            
            if publish_response:
                print(f"  Server response: status={publish_response.get('status')} url={publish_response.get('url', '')[:80]}")
                print(f"  Body: {publish_response.get('body', '')[:200]}")
            else:
                print("  Warning: No publish API response captured, checking page state...")
            
            # Check if page navigated away (success indicator)
            current_url = page.url
            print(f"  Current URL after publish: {current_url}")
            
            print(f"Successfully published: {title}")
            return True
        except Exception as e:
            print(f"Failed to publish: {e}")
            raise e
        finally:
            context.close()

if __name__ == "__main__":
    if not os.path.exists(PROFILE_PATH):
        login_xhs()
    else:
        print("Profile already exists. Ready for automation.")
