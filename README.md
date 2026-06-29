# 学科知识整合智能体

AI全栈极速黑客松项目 - 将多本教材整合压缩到30%，教学效果不打折。

## 项目简介

开发一个学科知识整合智能体，能够：
- 自动加载多本教材（PDF/MD/TXT/DOCX）
- 为每本教材构建知识图谱并可视化
- 跨教材识别知识点重叠、互补与缺失
- 整合压缩到不超过原始30%
- 基于整合后知识库进行RAG精准问答

## 环境依赖

| 环境 | 版本要求 |
|------|----------|
| Python | ≥3.9 |
| Node.js | ≥18.0 |

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/aueurm/ZJU-KnowledgeAgent.git
cd ZJU-KnowledgeAgent
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
npm install
```

## 配置说明

仓库提供 `.env.example` 作为配置模板。首次运行只需要复制模板并填入 `LLM_API_KEY`，其他变量可以保持默认：

```bash
cp .env.example .env
# Windows PowerShell 可用：Copy-Item .env.example .env
```

如果本机没有 `BAAI/bge-small-zh-v1.5` 缓存，系统会先用轻量内存检索兜底；需要更好的语义检索效果时，再配置本地 embedding 模型。

## 启动命令

### 一键启动

```bash
python start.py
```

启动后浏览器默认打开 `http://localhost:5173`；如果端口被占用，以终端输出的地址为准。

### 开发模式

```bash
# 启动后端
cd src/backend
python -m uvicorn app.main:app --reload --port 8000

# 另开终端，回到仓库根目录启动前端
npm run dev
```

### 生产模式

```bash
# 后端
cd src/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 另开终端，回到仓库根目录构建前端
npm run build
# 部署 src/frontend/dist 目录
```

## 使用说明

### 1. 上传教材

- 打开浏览器访问 `http://localhost:5173`
- 在左侧"教材管理"区域点击上传或拖拽文件
- 支持 PDF、Markdown、TXT、DOCX 格式

### 2. 查看知识图谱

- 上传成功后，点击教材列表中的教材
- 中间区域显示该教材的知识图谱
- 点击节点查看知识点详情

### 3. 跨教材整合

- 在右侧"整合操作"面板选择多本教材
- 点击"开始整合"执行跨教材知识整合
- 查看整合决策列表，确认或修改决策

### 4. RAG问答

- 切换到右侧"RAG问答"面板
- 输入问题，获取带引用来源的回答
- 点击引用查看原文内容

### 5. 对话交互

- 在"对话交互"面板与系统对话
- 可询问整合决策原因、要求修改决策

## 项目结构

```
ZJU-KnowledgeAgent/
├── docs/
│   ├── 需求分析.md        # 子问题分解与分析
│   ├── 系统设计.md        # 架构设计与API接口
│   └── Agent架构说明.md   # Agent设计决策论证
├── report/
│   └── 整合报告.md        # 整合结果报告
├── src/
│   ├── backend/           # FastAPI后端
│   └── frontend/          # Vue 3前端
├── requirements.txt       # Python依赖
├── package.json           # Node依赖
├── .env.example           # 环境变量模板
├── .gitignore
└── README.md
```

## 技术选型

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 前端框架 | Vue 3 |
| 图谱可视化 | AntV G6 |
| 大模型 | DeepSeek API |
| 向量嵌入 | BGE-small-zh |
| 向量检索 | ChromaDB |
| 文件解析 | PyMuPDF |

## 开源项目引用

- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架
- [Vue 3](https://vuejs.org/) - 前端框架
- [AntV G6](https://g6.antv.antgroup.com/) - 图谱可视化
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF解析

## 作者

浙江大学 - 黑客松参赛作品
