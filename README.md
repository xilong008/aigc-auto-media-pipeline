<div align="center">
  <h1>🚀 AIGC Auto-Media Pipeline</h1>
  <p><strong>全栈开源 · 零干预 · 爆款图文自动化分发中枢</strong></p>
  <p>将大模型思考、全网舆情爬取、生图渲染与 RPA 自动化发布融为一体的现代化自媒体运营平台。</p>
</div>

---

## 🌟 核心特性 (Features)

### 🧠 深度内容引擎 (Multi-Agent Pipeline)
抛弃传统的“水文”生成，系统内建了一套完整的多节点大模型工作流：
- **话题探针 (Topic Generator)**：支持输入宽泛领域，AI 自动生成最具爆发潜力的垂直话题。
- **情报溯源 (Web Search)**：基于搜狗搜索实时爬取全网最新舆情与爆文情报。
- **爆款基因解析 (Viral Genes)**：自动从情报中提炼 3 个核心情感钩子与反常识观点。
- **高阶文案合成 (Synthesis)**：注入设定的“专业人设”，生成 800-1000 字充满逻辑密度、带有强引流 CTA (Call to Action) 的精品长文，并自动匹配 ComfyUI 纯正英文提示词。

### 🎨 异构渲染管线 (Multi-Engine Rendering)
支持热切换多种生图引擎，平衡成本、速度与极致质量：
- 🌟 **SiliconFlow Kolors (硅基流动)**：零成本、国内极速出图。
- 🔮 **Gemini Imagen 3**：云端极速，高质量呈现。
- 🛠️ **ComfyUI 本地集群**：适配复杂工作流与极致出图要求，支持前端实时 WebSocket 进度回传。
- 🤖 **Antigravity 原生生图**：支持通过对话唤醒直接生成。

### 🤖 RPA 无人驾驶分发 (Stealth Automation)
摒弃容易被风控封号的非官方 API 逆向协议，采用底层真实的浏览器模拟：
- 基于 **Playwright + Stealth 插件** 实现物理级防反爬绕过。
- 本地加密留存会话 Cookie，无需反复登录。
- 控制台内嵌“一键扫码重新授权”功能，实时探测小红书等平台 Token 存活状态。
- **矩阵扩展计划**：UI 已预留抖音、快手、知乎的多渠道分发管线。

### ⚡ 现代化异步调度中枢 (Async Task Queue)
- 基于 FastAPI + SQLite (WAL模式) 构建的超轻量高并发调度中心。
- 绝不阻塞主事件循环，前台大屏通过 SSE (Server-Sent Events) **毫秒级实时打印后端终端日志**。
- 支持任务状态的动态流转（排队中 -> 渲染中 -> 装填发布中 -> 成功/失败）。

---

## 🛠️ 快速开始 (Quick Start)

### 1. 环境准备
需要安装 Python 3.9+ 及相关依赖环境。
```bash
# 克隆仓库
git clone https://github.com/your-username/aigc-automation.git
cd aigc-automation

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r src/requirements.txt

# 安装 Playwright 浏览器内核
playwright install chromium
```

### 2. 环境配置
复制环境变量模板并填入您的 API Keys：
```bash
cp src/.env.example src/.env
```
在 `.env` 中按需配置：
```env
# 大模型配置 (用于文案生成)
API_KEY=your_deepseek_or_other_llm_api_key
API_BASE_URL=https://api.deepseek.com
API_MODEL=deepseek-chat

# 生图引擎配置 (可选)
SILICONFLOW_API_KEY=your_siliconflow_key
```

### 3. 一键启动
系统自带了友好的启动脚本，首次启动会引导您扫码登录小红书保存持久化状态。
```bash
./start.sh
```
启动后，打开浏览器访问控制台大屏：**`http://127.0.0.1:8012`**

---

## 📺 控制台大屏一览 (Dashboard)

整个大屏基于 TailwindCSS + 原生 JS 构建，无繁重的前端框架依赖：
1. **任务数据舱**：可一键触发 AI 构思，或手动精调小红书标题、正文及 Prompt。
2. **终端日志投影**：左下角实时投射后台任务的执行轨迹与爆款基因分析结果。
3. **分发渠道授权管线**：直观展示当前多平台的 Token 健康度，提供一键重连唤醒。
4. **流水线实时状态**：支持分页的异步任务队列，查看生成结果与错误诊断。

---

## 📂 目录结构 (Structure)

```text
aigc-automation/
├── start.sh                  # 系统一键启动与初始化脚本
├── src/
│   ├── main.py               # FastAPI 调度中枢与路由
│   ├── database.py           # SQLite WAL并发表与队列管理
│   ├── llm_agent.py          # 多节点大模型情报爬取与文案生成
│   ├── dashboard.html        # 可视化调度大屏前端
│   ├── rpa_xiaohongshu.py    # 小红书自动化投递模块
│   ├── siliconflow_client.py # SiliconFlow 生图接口
│   ├── comfyui_client.py     # ComfyUI 调度与进度监听
│   ├── xhs_profile/          # Playwright 浏览器持久化配置(自动生成)
│   └── outputs/              # 自动保存的渲染成品图(自动生成)
└── README.md
```

---

## 🤝 参与贡献 (Contributing)

我们非常欢迎开发者加入这个开源项目！目前急需扩展的模块：
- [ ] 开发 `rpa_douyin.py` (抖音自动化投递引擎)
- [ ] 开发 `rpa_kuaishou.py` (快手自动化投递引擎)
- [ ] 开发 `rpa_zhihu.py` (知乎自动化投递引擎)

如果您有任何好的想法，欢迎提交 Pull Request 或发起 Issue！

## 📄 许可证 (License)

本项目基于 [MIT License](LICENSE) 开源，允许商用及二次开发。使用本系统造成的平台封号或法律风险由使用者自行承担。
