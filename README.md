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

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/aueurm/ZJU-.git
cd ZJU-
```

### 2. 后端安装

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 前端安装

```bash
npm install
```

## 配置说明

### 环境变量配置

创建 `.env` 文件（参考 `.env.example`）：

```env
# LLM API配置（必填）
LLM_API_KEY=your_api_key_here
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3
LLM_THINKING=disabled
LLM_EXTRACT_MAX_TOKENS=4096
EXTRACT_CONCURRENCY=3
MERGE_HIGH_THRESHOLD=0.92
MERGE_MID_THRESHOLD=0.80
MERGE_NAME_THRESHOLD=0.75
MIN_NODE_RETENTION=0.35
MIN_EDGE_RETENTION=0.50

# Embedding模型配置（可选，默认本地BGE）
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

# 服务端口（可选）
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

### .env.example

仓库提供 `.env.example` 作为配置模板，复制后填入实际值：

```bash
cp .env.example .env
# 编辑 .env 填入API密钥
```

## 启动命令

### 一键启动

```bash
python start.py
```

启动后浏览器会自动打开 `http://localhost:5173`。

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
# 部署dist目录
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

- 刬换到右侧"RAG问答"面板
- 输入问题，获取带引用来源的回答
- 点击引用查看原文内容

### 5. 对话交互

- 在"对话交互"面板与系统对话
- 可询问整合决策原因、要求修改决策

## 项目结构

```
ZJU-/
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
