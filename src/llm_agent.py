import os
import json
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

def _load_env():
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# ═══════════════════════════════════════════════════════════════════
# SOP 双轨加载系统：渠道SOP（怎么写）+ 行业SOP（写什么）
# ═══════════════════════════════════════════════════════════════════

# === 渠道SOP映射（平台规则：语气、结构、排版等） ===
_CHANNEL_SOP_MAP = {
    "小红书": "小红书爆款文案SOP.md",
    "xiaohongshu": "小红书爆款文案SOP.md",
    "xhs": "小红书爆款文案SOP.md",
    # 未来扩展更多渠道：
    # "抖音": "抖音短视频文案SOP.md",
    # "公众号": "公众号深度文章SOP.md",
    # "知乎": "知乎长文SOP.md",
}

# === 行业SOP映射（领域知识：术语、案例、痛点） ===
_INDUSTRY_SOP_MAP = {
    "装修": "SOP_装修设计.md", "设计": "SOP_装修设计.md", "全屋定制": "SOP_装修设计.md",
    "家装": "SOP_装修设计.md", "室内": "SOP_装修设计.md",
    "医美": "SOP_医美口腔.md", "口腔": "SOP_医美口腔.md", "皮肤": "SOP_医美口腔.md",
    "美容": "SOP_医美口腔.md", "整形": "SOP_医美口腔.md",
    "教育": "SOP_教育培训.md", "培训": "SOP_教育培训.md", "教培": "SOP_教育培训.md",
    "K12": "SOP_教育培训.md", "招生": "SOP_教育培训.md",
    "婚庆": "SOP_婚庆摄影.md", "婚纱": "SOP_婚庆摄影.md", "婚礼": "SOP_婚庆摄影.md",
    "摄影": "SOP_婚庆摄影.md",
    "餐饮": "SOP_本地生活.md", "民宿": "SOP_本地生活.md", "咖啡": "SOP_本地生活.md",
    "探店": "SOP_本地生活.md", "美食": "SOP_本地生活.md",
    "法律": "SOP_专业服务.md", "财税": "SOP_专业服务.md", "知识产权": "SOP_专业服务.md",
    "律师": "SOP_专业服务.md", "会计": "SOP_专业服务.md",
}

def _load_channel_sop(channel: str = "小红书", logger_cb=print) -> str:
    """加载渠道SOP（平台规则：怎么写）"""
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    matched_file = None
    for keyword, filename in _CHANNEL_SOP_MAP.items():
        if keyword in channel:
            matched_file = filename
            break
    if not matched_file:
        matched_file = "小红书爆款文案SOP.md"  # 默认渠道
    sop_path = os.path.join(docs_dir, matched_file)
    if os.path.exists(sop_path):
        with open(sop_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger_cb(f"[Pipeline] 📺 已加载渠道SOP: {matched_file}")
        return content
    logger_cb("[Pipeline] ⚠️ 未找到渠道SOP文档")
    return ""

def _load_industry_sop(domain: str, logger_cb=print) -> str:
    """加载行业SOP（领域知识：写什么）"""
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    matched_file = None
    for keyword, filename in _INDUSTRY_SOP_MAP.items():
        if keyword in domain:
            matched_file = filename
            break
    if matched_file:
        sop_path = os.path.join(docs_dir, matched_file)
        if os.path.exists(sop_path):
            with open(sop_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger_cb(f"[Pipeline] 🏭 已加载行业SOP: {matched_file}")
            return content
    logger_cb("[Pipeline] ⚠️ 未匹配到行业定制SOP，将仅使用渠道SOP通用规则")
    return ""

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

def generate_content_payload(domain: str = "", persona: str = "", topic_input: str = "", channel: str = "小红书", logger_cb=print):
    """多智体流水线生成核心（支持多渠道 + 多行业双轨SOP）"""
    _load_env()
    
    # === Node 1: Topic Generator (话题探针) ===
    logger_cb(f"[Pipeline] 🚀 1. 进入话题判定节点... (渠道={channel}, 行业={domain}, persona={persona}, topic={topic_input})")
    
    if topic_input:
        topic = topic_input
        logger_cb(f"[Pipeline] 🎯 使用用户指定的精准话题: {topic}")
    else:
        if not domain:
            domain = "职场提效、个人成长、搞钱思路、AI工具实操"
            
        topic_prompt = f"请在“{domain}”领域下，随机构思一个当前在{channel}上极具爆发潜力的垂直话题，只需输出核心关键词（控制在10字以内，例如：打工人用AI做副业）。"
        topic = _get_llm_response(topic_prompt, max_tokens=100).strip().replace("\"", "")
        logger_cb(f"[Pipeline] 🎯 锁定随机垂直话题: {topic}")
    
    # === Node 2: Search Engine (情报溯源) ===
    logger_cb("[Pipeline] 🌐 2. 爬取互联网舆情情报...")
    search_results = _search_web(f"知乎 {channel} {topic}", logger_cb=logger_cb)
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
    
    # === Node 3: SOP-Driven Synthesis (SOP驱动的精品生成) ===
    logger_cb("[Pipeline] 🧠 3. 双轨SOP注入：渠道规则 + 行业知识，开启终端图文生成...")
    if not persona:
        persona_str = '极其资深的"爆款内容操盘手"和"舆情分析专家"'
    else:
        persona_str = persona

    # ═══════════════════════════════════════════════════════════════════
    # 双轨SOP加载：渠道SOP（怎么写）+ 行业SOP（写什么）
    # ═══════════════════════════════════════════════════════════════════
    channel_sop = _load_channel_sop(channel=channel, logger_cb=logger_cb)
    industry_sop = _load_industry_sop(domain or topic_input or "", logger_cb=logger_cb)

    # 动态组装 System Prompt = 人设 + 渠道SOP + 行业SOP
    sys_prompt = f"""你是一个{persona_str}。
你的任务是将收集到的外界杂乱情报，深度洗稿、提取核心痛点，并注入你的独家视角和专业设定。

你必须严格遵循以下两套规则：
- 【渠道SOP】决定你的文章结构、语气、排版风格（怎么写）
- 【行业SOP】提供你的行业术语、案例素材、痛点场景（写什么）

两者缺一不可。渠道SOP确保文章符合平台调性，行业SOP确保内容具备专业深度。

{'='*60}
【渠道SOP — 平台规则（必须严格执行）】
{'='*60}
{channel_sop}

{'='*60}
【行业SOP — 领域专业知识（务必参考其中的行业术语、案例风格和配图指引）】
{'='*60}
{industry_sop if industry_sop else '（未匹配到行业定制SOP，请根据话题自行运用专业知识，但仍需遵循渠道SOP的结构和语气要求）'}

确保最终输出的文本绝不是泛泛而谈的AI套话，而是充分体现你的身份特色、立场极度鲜明、有理有据的高质量爆款！
"""

    synthesis_prompt = f"""我们要针对话题：【{topic}】写一篇{channel}顶级爆款长文。

【已提炼的核心爆款基因（必须作为文章骨架深度植入）：】
{viral_genes}

【网络最新情报参考（作为素材补充）：】
{insight_context}

【输出要求 — 请直接返回严格的 JSON，确保可被 JSON.parse 解析！不要用 Markdown 代码块！不要有多余废话！】

包含以下三个核心字段：

1. "title": {channel}爆款标题
   - 带Emoji，悬念+痛点结合，20字以内
   - 要有极强的点击欲望

2. "body": 正文（800~1000字深度长文）
   ⚠️ 必须严格遵循 System Prompt 中的 AIDA 四段式结构：
   - 第一段 Attention (约15%): 直接甩出痛点场景/颠覆认知的结论
   - 第二段 Interest (约30%): 用真实惨案+量化数据+行业专业术语佐证
   - 第三段 Desire (约40%): 给出"拿来就能用"的极具体操作方案（不是大方向！）
   - 第四段 Action (约15%): 自然真诚的私域引流钩子 + 评论区互动引导

   质量自检清单（输出前在内心过一遍，不通过则重写）：
   ✅ 全文至少包含 2 个具体数字或真实案例？
   ✅ 至少使用了 2-3 个只有业内人士才知道的硬核专业术语？
   ✅ 有"别不信"、"听我一句劝"、"我见过最惨的"这类口语化引导？
   ✅ 排版清爽？使用了 Emoji 视觉引导？短句多于长难句？

   末尾必须带上3-5个话题标签#。

3. "prompts": 配图提示词列表（纯英文JSON数组，必须3-5张图）
   每张图要求：画面必须非常漂亮、好看、赏心悦目，符合大众审美。
   每条末尾必须附加: beautiful, aesthetically pleasing, high quality, 8k
   每条30-50英文单词，禁止中文。
   图片分工：
   - 第1张：封面主图（最吸睛的核心场景，色彩鲜艳构图讲究）
   - 第2张：痛点/问题的视觉化呈现
   - 第3张：正确做法/解决方案展示
   - 第4张（可选）：专业细节特写
   - 第5张（可选）：温暖高级的生活氛围
"""

    final_output = _get_llm_response(synthesis_prompt, sys_prompt=sys_prompt, max_tokens=3000)
    final_output = final_output.replace("```json", "").replace("```", "").strip()

    try:
        parsed_json = json.loads(final_output)
    except json.JSONDecodeError:
        raise Exception(f"大模型未能输出合法 JSON (最终输出截断)：{final_output[:200]}")

    # === Node 4: SOP Quality Gate (SOP合规校验) ===
    logger_cb("[Pipeline] 🔍 4. 启动SOP合规校验（论据浓度/行业深度/情绪价值/排版质量）...")

    body_text = parsed_json.get("body", "")
    check_prompt = f"""你是一个严格的内容质检官。请对以下{channel}正文进行SOP合规校验。

【待校验正文】：
{body_text}

【校验标准 — 4项全部必须通过】：
1. 论据浓度校验：全文是否至少包含 2 个具体的数字或真实案例？
2. 行业深度校验：是否使用了 2-3 个只有业内人士才知道的硬核专业术语？
3. 情绪价值校验：是否有"别不信"、"听我一句劝"、"我见过最惨的"这种拉近距离的口语化引导？
4. 降维打击校验：排版是否清爽？是否使用了 Emoji 作为视觉引导？短句是否多于长难句？

请严格返回 JSON 格式（不要 Markdown 代码块）：
{{"pass": true/false, "score": 0-10, "issues": ["不通过的具体原因，如果全部通过则为空数组"]}}
"""

    try:
        check_output = _get_llm_response(check_prompt, sys_prompt="你是一个严格的内容质检AI，只输出JSON。", max_tokens=500)
        check_output = check_output.replace("```json", "").replace("```", "").strip()
        check_result = json.loads(check_output)

        score = check_result.get("score", 0)
        passed = check_result.get("pass", False)
        issues = check_result.get("issues", [])

        if passed and score >= 7:
            logger_cb(f"[Pipeline] ✅ SOP合规校验通过！质量评分: {score}/10")
        else:
            issue_str = "；".join(issues) if issues else "未达标"
            logger_cb(f"[Pipeline] ⚠️ SOP校验评分: {score}/10 | 问题: {issue_str}")
            logger_cb("[Pipeline] 🔄 触发SOP修复重写...")

            # 用校验反馈驱动一次修复重写
            fix_prompt = f"""以下是一篇{channel}正文，经过SOP质检发现了问题：

【原文】：
{body_text}

【质检反馈】：
评分：{score}/10
问题：{issue_str}

请根据反馈修复这篇正文，确保：
1. 至少包含 2 个具体数字和真实案例
2. 使用 2-3 个业内专业术语
3. 有口语化的情感引导表达
4. 排版清爽，有 Emoji，短句为主
5. 末尾有私域引流钩子和3-5个话题标签#
6. 总字数 800-1000 字

只输出修复后的正文，不要任何额外解释。"""

            fixed_body = _get_llm_response(fix_prompt, sys_prompt=sys_prompt, max_tokens=2500).strip()
            if len(fixed_body) > 200:  # 确保修复输出有效
                parsed_json["body"] = fixed_body
                logger_cb("[Pipeline] ✅ SOP修复重写完成！")
            else:
                logger_cb("[Pipeline] ⚠️ 修复输出过短，保留原文")
    except Exception as e:
        logger_cb(f"[Pipeline] ⚠️ SOP校验模块异常（不影响主流程）: {str(e)}")

    # 最终清理 prompts 中的中文字符 + 兼容旧格式
    if "prompts" in parsed_json and isinstance(parsed_json["prompts"], list):
        parsed_json["prompts"] = [
            re.sub(r'[\u4e00-\u9fff]+', '', p).strip() for p in parsed_json["prompts"]
        ]
        parsed_json["prompt"] = parsed_json["prompts"][0] if parsed_json["prompts"] else ""
        logger_cb(f"[Pipeline] 🖼️ 已生成 {len(parsed_json['prompts'])} 张配图提示词")
    elif "prompt" in parsed_json:
        cleaned = re.sub(r'[\u4e00-\u9fff]+', '', parsed_json["prompt"]).strip()
        parsed_json["prompt"] = cleaned
        parsed_json["prompts"] = [cleaned]
        logger_cb("[Pipeline] 🖼️ 单图模式（已自动转为 prompts 数组）")

    logger_cb("[Pipeline] ✅ 全流程装配完成！文案已通过SOP质量关卡。")
    return parsed_json
