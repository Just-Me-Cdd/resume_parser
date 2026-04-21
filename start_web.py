"""
简历解析工具 - Web 服务启动脚本
"""
import sys
import os
from pathlib import Path

# 禁用 PaddlePaddle 模型源检查，避免启动阻塞
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# 确保项目根目录在 Python 路径中
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import uvicorn
from web_app import app

if __name__ == "__main__":
    print("=" * 60)
    print("简历解析工具 - Web 服务")
    print("=" * 60)
    print("服务地址: http://127.0.0.1:8000")
    print("API 文档: http://127.0.0.1:8000/docs")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )