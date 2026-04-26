import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

def _load_env():
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

def _get_llm_response(prompt: str, sys_prompt: str = "你是一个专业的数据分析与内容重构AI。", max_tokens: int = 1500) -> str:
    """内部通用大模型调用封装 - 应对各类代理节点的异构返回"""
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("API_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("API_MODEL", "deepseek-chat")
    
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        raise Exception("API Key 尚未配置！请打开 src/.env 文件填入。")
        
    endpoint = base_url.rstrip('/')
    if not endpoint.endswith('v1'):
        endpoint = f"{endpoint}/v1"
    endpoint = f"{endpoint}/chat/completions"
        
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": True  # MUST use stream to prevent Aliyun API gateway timeout on 120s+ tasks
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "OpenAI/v1 (Python; Dashscope)"
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10, stream=True)
        response.raise_for_status() 
        
        content = ""
        # 流式解析，防止网关大促引发大段延迟和读超时
        for line in response.iter_lines():
            if not line: continue
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data: ') and decoded_line != 'data: [DONE]':
                try:
                    chunk = json.loads(decoded_line[6:])
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            content += delta["content"]
                        elif "output" in chunk and "text" in chunk["output"]:
                            # fallback for older models
                            content = chunk["output"]["text"]
                except:
                    pass
                    
        return content
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" | Response: {e.response.text[:300]}"
        raise Exception(f"大模型网络通讯错误：{error_msg}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"大模型解析异常: {str(e)}")

def _search_web(topic: str, logger_cb=print) -> list:
    """简易轻量化搜狗舆情数据爬虫节点"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }
    try:
        res = requests.get(f"https://www.sogou.com/web?query={topic}", headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        
        # 多维解析，适配不同的搜狗前端结构
        for div in soup.find_all('div', class_='vrwrap', limit=6):
            h3 = div.find('h3')
            title = h3.text.strip() if h3 else ""
            p = div.find('div', class_='text-layout') or div.find('p') or div.find('div', class_='fz-mid')
            snippet = p.text.strip() if p else ""
            if title and snippet:
                results.append(f"【{title}】: {snippet}")
                
        if len(results) < 3:
            for div in soup.find_all('div', class_='rb', limit=6):
                h3 = div.find('h3')
                title = h3.text.strip() if h3 else ""
                p = div.find('div', class_='ft')
                snippet = p.text.strip() if p else ""
                if title and snippet:
                    results.append(f"【{title}】: {snippet}")
        return results
    except Exception as e:
        logger_cb(f"[Pipeline] ⚠️ 搜索节点告警: {e}")
        return []

def generate_content_payload(domain: str = "", persona: str = "", topic_input: str = "", logger_cb=print):
    """多智体流水线生成核心"""
    _load_env()
    
    # === Node 1: Topic Generator (话题探针) ===
    logger_cb(f"[Pipeline] 🚀 1. 进入话题判定节点... (参数 domain={domain}, persona={persona}, topic={topic_input})")
    
    if topic_input:
        topic = topic_input
        logger_cb(f"[Pipeline] 🎯 使用用户指定的精准话题: {topic}")
    else:
        if not domain:
            domain = "职场提效、个人成长、搞钱思路、AI工具实操"
            
        topic_prompt = f"请在“{domain}”领域下，随机构思一个当前在小红书上极具爆发潜力的垂直话题，只需输出核心关键词（控制在10字以内，例如：打工人用AI做副业）。"
        topic = _get_llm_response(topic_prompt, max_tokens=100).strip().replace("\"", "")
        logger_cb(f"[Pipeline] 🎯 锁定随机垂直话题: {topic}")
    
    # === Node 2: Search Engine (情报溯源) ===
    logger_cb("[Pipeline] 🌐 2. 爬取互联网舆情情报...")
    search_results = _search_web(f"知乎 小红书 {topic}", logger_cb=logger_cb)
    insight_context = "无外部网络参考，请发挥大模型本身认知。"
    if search_results:
        insight_context = "\n".join(search_results)
        logger_cb(f"[Pipeline] 📖 成功捕获 {len(search_results)} 条热门情报")
    else:
        logger_cb(f"[Pipeline] ⚠️ 搜索无结果，转为纯大模型直出")
    
    # === Node 2.5: Insight Analysis (爆款基因解析) ===
    logger_cb("[Pipeline] 🧬 2.5. 深度解析全网热点，提取爆款基因...")
    analysis_prompt = f"""
    基于以下针对话题【{topic}】的全网最新情报：
    {insight_context}
    
    请分析当前该行业内的最新热点和流量密码，提取出 3 个核心“爆款基因”（即最容易引发用户转发、点赞、收藏或争论的情感钩子、反常识观点、或核心痛点）。
    输出要求：只输出这3个爆款基因的精炼总结，总计不超过150字，不要任何废话。
    """
    viral_genes = _get_llm_response(analysis_prompt, max_tokens=300).strip()
    logger_cb(f"[Pipeline] 💡 成功提取爆款基因: {viral_genes[:50]}...")
    
    # === Node 3 & 4: Insight & Synthesize (洞察提纯与精品生成) ===
    logger_cb("[Pipeline] 🧠 3/4. 开启深度洞察提取与终端图文生成...")
    if not persona:
        persona_str = "极其资深的“爆款内容操盘手”和“舆情分析专家”"
    else:
        persona_str = persona

    sys_prompt = f"""
    你是一个{persona_str}。
    你的任务是将收集到的外界杂乱情报，深度洗稿、提取核心痛点，并注入你的独家视角和专业设定。
    确保最终输出的文本绝不是泛泛而谈的AI套话，而是：
    1. 充分体现【{persona_str}】身份特色与极高专业度；
    2. 立场极度鲜明，观点犀利甚至有些反常识，直击用户痛点与行业内幕；
    3. 充满逻辑密度，能够引发用户强烈共鸣；
    4. 带有极强的商业转化思维，能在潜移默化中引导高意向客户主动咨询。
    """
    
    synthesis_prompt = f"""
    我们要针对话题：【{topic}】写一篇小红书顶级爆款长文。
    
    【已提炼的核心爆款基因（必须作为文章骨架深度植入）：】
    {viral_genes}
    
    【网络最新情报参考（作为素材补充）：】
    {insight_context}
    
    【输出要求：】
    请直接返回严格的 JSON 格式数据，确保可以直接被 JSON.parse 解析！不要使用 Markdown 代码块！不要有多余的废话！
    包含以下三个核心字段：
    - "title": (带Emoji，悬念+痛点结合，20字以内，要有极强的点击欲望)
    - "body": (必须是一篇800~1000字的深度长文。要求：1. 开篇直击痛点或抛出反常识观点；2. 中间提供2-3个干货十足、极其专业的实战经验或独家洞察；3. 语气真诚、干脆、金句频出；4. 在结尾处必须设置引流钩子（Call to Action），用专业的话术引导客户在评论区留言、或者私信咨询定制方案/获取核心资料；5. 结尾带上3-5个相关话题标签#)
    - "prompt": (提取文章核心意象，写一段用于 ComfyUI 生成高端封面的纯正英文提示词，必须以 masterpiece, ultra-detailed, best quality 开头，包含光影、材质、构图等细节描述)
    """
    
    final_output = _get_llm_response(synthesis_prompt, sys_prompt=sys_prompt, max_tokens=2500)
    final_output = final_output.replace("```json", "").replace("```", "").strip()
    
    try:
        parsed_json = json.loads(final_output)
        logger_cb("[Pipeline] ✅ 精品文案装配完成！(JSON解析通过)")
        return parsed_json
    except json.JSONDecodeError:
        raise Exception(f"大模型未能输出合法 JSON (最终输出截断)：{final_output[:200]}")
