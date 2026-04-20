# 简历解析工具

一个功能完整的简历解析工具，支持图片、PDF、Word 等多种格式，自动提取结构化信息，预留 RAG 检索接口。

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
cd ~/resume_parser

# 启动服务
docker-compose up -d

# 或使用便捷脚本
chmod +x start-docker.sh
./start-docker.sh up
```

访问 **http://localhost:8000**

### 方式二：本地运行

```bash
cd ~/resume_parser

# 安装依赖
pip install -r requirements.txt

# 启动服务
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
python web_app.py
```

---

## 🐳 Docker 部署

### 前置要求

- Docker 20.10+
- docker-compose 1.29+

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 重新构建
docker-compose up -d --build
```

### 使用 GPU 加速（如已安装 nvidia-docker）

如需使用 GPU 加速 OCR，使用默认的 `Dockerfile`（已包含 CUDA 支持的 paddlepaddle）。

---

## 🌐 Web 界面功能

| 功能 | 说明 |
|------|------|
| 📤 拖拽上传 | 将简历文件拖拽到上传区域 |
| 📋 批量选择 | 支持一次选择多个文件 |
| 📊 实时统计 | 显示已解析简历数、章节数 |
| 🔍 RAG 搜索 | 对简历内容进行关键词检索 |
| 🎴 卡片展示 | 美观的卡片式简历展示 |
| 📑 章节分类 | 自动识别教育/工作/技能等章节 |
| 🗑️ 清空功能 | 一键清空所有解析结果 |

---

## 📡 API 接口

### 上传并解析简历
```bash
POST /api/upload
Content-Type: multipart/form-data
files: 简历文件（支持多个）
```

### RAG 搜索
```bash
GET /api/rag/search?q=Python开发&top_k=5
```

### 获取统计信息
```bash
GET /api/stats
```

---

## 📁 项目结构

```
resume_parser/
├── web_app.py              # Web 服务入口
├── main.py                 # CLI 入口
├── config.py               # 配置文件
├── requirements.txt       # 依赖列表
├── Dockerfile             # GPU 版本
├── Dockerfile.cpu        # CPU 版本
├── docker-compose.yml     # Docker Compose 配置
├── start-docker.sh       # Docker 便捷启动脚本
├── parser/               # 解析器
├── preprocessor/         # 预处理
├── ocr/                  # OCR 模块
├── extractor/            # 内容提取
├── storage/              # RAG 存储
└── models/               # 数据模型
```

---

## 📝 Python API

```python
from parser.auto_detect import AutoDetectParser

parser = AutoDetectParser(lang="ch")
resume = parser.parse("resume.jpg")

for section in resume.sections:
    print(f"【{section.title}】{section.content}")

# 转为 JSON
json_data = resume.to_dict()
```

---

## 📄 许可证

MIT License
