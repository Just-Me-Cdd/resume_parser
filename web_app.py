#!/usr/bin/env python3
"""
简历解析工具 - Web 服务
基于 FastAPI + Vue3
"""

import os
import sys

# 禁用 PaddlePaddle 模型源检查，避免启动阻塞
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import json
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from parser.auto_detect import AutoDetectParser
from models.resume import Resume
from storage.rag_retriever import RAGRetriever
from utils.logger import setup_logger, get_logger

logger = setup_logger("resume_parser_web")

# 创建 FastAPI 应用
app = FastAPI(
    title="简历解析工具",
    description="支持图片、PDF、Word 格式的简历解析服务",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 解析器实例
parser = AutoDetectParser(default_lang="ch", default_mode="text")
rag_retriever = RAGRetriever(store_type="simple")

# 上传目录
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 挂载静态文件
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ==================== API 路由 ====================

class ResumeSectionResponse(BaseModel):
    title: str
    content: str
    confidence: float


class ResumeResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    parsed_at: str
    sections: List[ResumeSectionResponse]
    raw_text: str
    stats: dict


class ParseRequest(BaseModel):
    lang: Optional[str] = "ch"
    mode: Optional[str] = "text"


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回主页"""
    return get_index_html()


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    上传并解析简历文件
    
    - 支持批量上传
    - 自动识别文件类型
    - 返回解析结果
    """
    results = []
    
    for file in files:
        try:
            # 检查文件类型
            ext = Path(file.filename).suffix.lower()
            supported_exts = AutoDetectParser.get_supported_extensions()
            
            if ext not in supported_exts:
                results.append({
                    "success": False,
                    "file_name": file.filename,
                    "error": f"不支持的文件类型: {ext}，支持的类型: {', '.join(supported_exts)}"
                })
                continue
            
            # 保存文件
            file_path = UPLOAD_DIR / file.filename
            content = await file.read()
            file_path.write_bytes(content)
            
            # 解析简历
            try:
                resume = parser.parse(file_path)
                
                # 添加到 RAG
                rag_retriever.add_resume(resume)
                
                results.append({
                    "success": True,
                    "file_name": resume.file_name,
                    "file_type": resume.file_type,
                    "parsed_at": resume.parsed_at.isoformat(),
                    "sections": [s.model_dump() for s in resume.sections],
                    "stats": {
                        "section_count": len(resume.sections),
                        "raw_text_length": len(resume.raw_text)
                    }
                })
                
                logger.info(f"成功解析: {file.filename}")
                
            except Exception as e:
                logger.error(f"解析失败 {file.filename}: {e}")
                results.append({
                    "success": False,
                    "file_name": file.filename,
                    "error": str(e)
                })
                
        except Exception as e:
            logger.error(f"上传失败 {file.filename if file else 'unknown'}: {e}")
            results.append({
                "success": False,
                "file_name": file.filename if file else "unknown",
                "error": str(e)
            })
    
    # 统计
    success_count = sum(1 for r in results if r.get("success", False))
    
    return JSONResponse({
        "total": len(results),
        "success": success_count,
        "failed": len(results) - success_count,
        "results": results
    })


@app.post("/api/parse")
async def parse_resume(file: UploadFile = File(...), lang: str = "ch", mode: str = "text"):
    """
    解析单个简历文件
    """
    # 检查文件类型
    ext = Path(file.filename).suffix.lower()
    supported_exts = AutoDetectParser.get_supported_extensions()
    
    if ext not in supported_exts:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")
    
    # 保存文件
    file_path = UPLOAD_DIR / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    
    # 解析
    try:
        resume = parser.parse(file_path)
        rag_retriever.add_resume(resume)
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": resume.file_name,
                "file_name": resume.file_name,
                "file_type": resume.file_type,
                "parsed_at": resume.parsed_at.isoformat(),
                "sections": [s.model_dump() for s in resume.sections],
                "raw_text": resume.raw_text,
                "stats": {
                    "section_count": len(resume.sections),
                    "raw_text_length": len(resume.raw_text)
                }
            }
        })
    except Exception as e:
        logger.error(f"解析失败 {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resumes")
async def list_resumes():
    """获取已解析的简历列表"""
    stats = rag_retriever.get_stats()
    return JSONResponse({
        "total_sections": stats["total_sections"],
        "store_type": stats["store_type"]
    })


@app.get("/api/rag/search")
async def search_resumes(q: str, top_k: int = 5):
    """RAG 检索"""
    try:
        results = rag_retriever.retrieve(q, top_k=top_k)
        
        return JSONResponse({
            "query": q,
            "count": len(results),
            "results": [
                {
                    "resume_id": r.resume_id,
                    "title": r.section.title,
                    "content": r.section.content,
                    "score": r.score
                }
                for r in results
            ]
        })
    except Exception as e:
        logger.error(f"检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/resumes")
async def clear_resumes():
    """清空知识库"""
    rag_retriever.clear()
    return JSONResponse({"success": True, "message": "知识库已清空"})


@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    stats = rag_retriever.get_stats()
    return JSONResponse(stats)


# ==================== 前端页面 ====================

def get_index_html() -> str:
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>简历解析工具 - 智能简历处理平台</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4F46E5;
            --primary-dark: #4338CA;
            --primary-light: #818CF8;
            --success: #10B981;
            --warning: #F59E0B;
            --error: #EF4444;
            --bg-primary: #F8FAFC;
            --bg-secondary: #FFFFFF;
            --bg-tertiary: #F1F5F9;
            --text-primary: #1E293B;
            --text-secondary: #64748B;
            --text-tertiary: #94A3B8;
            --border: #E2E8F0;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 16px;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 40px 0 80px;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            opacity: 0.5;
        }
        
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            position: relative;
            z-index: 1;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .logo-icon {
            width: 48px;
            height: 48px;
            background: rgba(255,255,255,0.2);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .logo h1 {
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        
        .header p {
            font-size: 18px;
            opacity: 0.9;
            max-width: 600px;
        }
        
        /* Main Container */
        .main-container {
            max-width: 1200px;
            margin: -60px auto 40px;
            padding: 0 24px;
            position: relative;
            z-index: 2;
        }
        
        /* Upload Card */
        .upload-card {
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            padding: 32px;
            margin-bottom: 32px;
        }
        
        .upload-zone {
            border: 2px dashed var(--border);
            border-radius: var(--radius-md);
            padding: 60px 40px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            background: var(--bg-tertiary);
        }
        
        .upload-zone:hover, .upload-zone.dragover {
            border-color: var(--primary);
            background: rgba(79, 70, 229, 0.05);
        }
        
        .upload-zone.dragover {
            transform: scale(1.01);
        }
        
        .upload-icon {
            width: 80px;
            height: 80px;
            margin: 0 auto 24px;
            background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            color: white;
            box-shadow: 0 8px 32px rgba(79, 70, 229, 0.3);
        }
        
        .upload-zone h3 {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-primary);
        }
        
        .upload-zone p {
            color: var(--text-secondary);
            margin-bottom: 20px;
        }
        
        .upload-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 14px 28px;
            border-radius: var(--radius-md);
            font-weight: 600;
            font-size: 15px;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
        }
        
        .upload-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
        }
        
        .upload-hint {
            margin-top: 16px;
            font-size: 13px;
            color: var(--text-tertiary);
        }
        
        .file-input {
            display: none;
        }
        
        /* Options Bar */
        .options-bar {
            display: flex;
            gap: 16px;
            margin-top: 24px;
            flex-wrap: wrap;
        }
        
        .option-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .option-label {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .option-select {
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 14px;
            background: white;
            color: var(--text-primary);
            cursor: pointer;
            outline: none;
            transition: border-color 0.2s;
        }
        
        .option-select:focus {
            border-color: var(--primary);
        }
        
        /* Results Section */
        .results-section {
            margin-top: 40px;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
        }
        
        .section-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .section-title h2 {
            font-size: 22px;
            font-weight: 700;
        }
        
        .badge {
            background: var(--primary);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }
        
        .badge-success {
            background: var(--success);
        }
        
        .badge-warning {
            background: var(--warning);
        }
        
        .clear-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            background: white;
            color: var(--text-secondary);
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .clear-btn:hover {
            border-color: var(--error);
            color: var(--error);
            background: rgba(239, 68, 68, 0.05);
        }
        
        /* Resume Cards */
        .resume-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 24px;
        }
        
        .resume-card {
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            overflow: hidden;
            transition: all 0.3s ease;
            animation: fadeInUp 0.4s ease;
        }
        
        .resume-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .card-header {
            background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .card-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .file-icon {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%);
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
        }
        
        .file-info h3 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .file-info span {
            font-size: 13px;
            color: var(--text-tertiary);
        }
        
        .card-actions {
            display: flex;
            gap: 8px;
        }
        
        .action-btn {
            width: 36px;
            height: 36px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            background: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            font-size: 16px;
        }
        
        .action-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        
        .card-body {
            padding: 24px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .card-body::-webkit-scrollbar {
            width: 6px;
        }
        
        .card-body::-webkit-scrollbar-track {
            background: var(--bg-tertiary);
            border-radius: 3px;
        }
        
        .card-body::-webkit-scrollbar-thumb {
            background: var(--text-tertiary);
            border-radius: 3px;
        }
        
        /* Section Items */
        .section-item {
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }
        
        .section-item:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }
        
        .section-header-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
        }
        
        .section-tag {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .section-tag.education {
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        }
        
        .section-tag.experience {
            background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        }
        
        .section-tag.skills {
            background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
        }
        
        .section-confidence {
            font-size: 11px;
            color: var(--text-tertiary);
            margin-left: auto;
        }
        
        .section-content {
            color: var(--text-secondary);
            font-size: 14px;
            line-height: 1.7;
            white-space: pre-wrap;
            word-break: break-word;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 80px 40px;
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
        }
        
        .empty-icon {
            width: 120px;
            height: 120px;
            margin: 0 auto 24px;
            background: var(--bg-tertiary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
        }
        
        .empty-state h3 {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .empty-state p {
            color: var(--text-secondary);
        }
        
        /* Loading State */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.95);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s;
        }
        
        .loading-overlay.active {
            opacity: 1;
            visibility: visible;
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Toast Notifications */
        .toast-container {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 1001;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .toast {
            background: white;
            padding: 16px 20px;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideIn 0.3s ease;
            min-width: 300px;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .toast.success {
            border-left: 4px solid var(--success);
        }
        
        .toast.error {
            border-left: 4px solid var(--error);
        }
        
        .toast-icon {
            font-size: 20px;
        }
        
        .toast.success .toast-icon { color: var(--success); }
        .toast.error .toast-icon { color: var(--error); }
        
        .toast-message {
            flex: 1;
            font-size: 14px;
        }
        
        /* Search Bar */
        .search-section {
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            padding: 24px;
            margin-bottom: 32px;
        }
        
        .search-bar {
            display: flex;
            gap: 12px;
        }
        
        .search-input-wrapper {
            flex: 1;
            position: relative;
        }
        
        .search-input {
            width: 100%;
            padding: 14px 16px 14px 48px;
            border: 2px solid var(--border);
            border-radius: var(--radius-md);
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }
        
        .search-input:focus {
            border-color: var(--primary);
        }
        
        .search-icon {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 18px;
            color: var(--text-tertiary);
        }
        
        .search-btn {
            padding: 14px 28px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            border: none;
            border-radius: var(--radius-md);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .search-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
        }
        
        /* Stats Bar */
        .stats-bar {
            display: flex;
            gap: 24px;
            margin-bottom: 24px;
        }
        
        .stat-item {
            background: var(--bg-secondary);
            padding: 16px 24px;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-sm);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .stat-icon {
            width: 44px;
            height: 44px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .stat-icon.primary {
            background: rgba(79, 70, 229, 0.1);
            color: var(--primary);
        }
        
        .stat-icon.success {
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .stat-label {
            font-size: 13px;
            color: var(--text-tertiary);
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 40px 24px;
            color: var(--text-tertiary);
            font-size: 14px;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .resume-grid {
                grid-template-columns: 1fr;
            }
            
            .stats-bar {
                flex-wrap: wrap;
            }
            
            .options-bar {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="spinner"></div>
    </div>
    
    <!-- Toast Container -->
    <div class="toast-container" id="toastContainer"></div>
    
    <!-- Header -->
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon">📋</div>
                <h1>简历解析工具</h1>
            </div>
            <p>智能简历批量处理平台 - 支持图片、PDF、Word格式，自动提取结构化信息</p>
        </div>
    </header>
    
    <!-- Main Container -->
    <div class="main-container">
        <!-- Upload Card -->
        <div class="upload-card">
            <div class="upload-zone" id="uploadZone">
                <div class="upload-icon">📤</div>
                <h3>拖拽简历文件到这里</h3>
                <p>或点击下方按钮选择文件</p>
                <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                    <span>📁</span> 选择简历文件
                </button>
                <input type="file" id="fileInput" class="file-input" multiple accept=".jpg,.jpeg,.png,.pdf,.docx,.doc">
                <p class="upload-hint">支持 JPG、PNG、PDF、DOCX 格式，可批量选择</p>
            </div>
            
            <div class="options-bar">
                <div class="option-group">
                    <span class="option-label">识别语言:</span>
                    <select class="option-select" id="langSelect">
                        <option value="ch">中文</option>
                        <option value="en">英文</option>
                        <option value="chinese_cht">繁体中文</option>
                    </select>
                </div>
                <div class="option-group">
                    <span class="option-label">PDF模式:</span>
                    <select class="option-select" id="modeSelect">
                        <option value="text">文本提取</option>
                        <option value="ocr">OCR识别</option>
                    </select>
                </div>
            </div>
        </div>
        
        <!-- Search Section -->
        <div class="search-section">
            <div class="search-bar">
                <div class="search-input-wrapper">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="search-input" id="searchInput" placeholder="搜索简历内容，如：Python开发、清华大学...">
                </div>
                <button class="search-btn" onclick="searchResumes()">搜索</button>
            </div>
        </div>
        
        <!-- Stats Bar -->
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-icon primary">📊</div>
                <div>
                    <div class="stat-value" id="totalResumes">0</div>
                    <div class="stat-label">已解析简历</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon success">📑</div>
                <div>
                    <div class="stat-value" id="totalSections">0</div>
                    <div class="stat-label">提取章节数</div>
                </div>
            </div>
        </div>
        
        <!-- Results Section -->
        <div class="results-section">
            <div class="section-header">
                <div class="section-title">
                    <h2>解析结果</h2>
                    <span class="badge" id="resultCount">0</span>
                </div>
                <button class="clear-btn" onclick="clearAll()">
                    <span>🗑️</span> 清空全部
                </button>
            </div>
            
            <!-- Results Grid -->
            <div class="resume-grid" id="resultsGrid">
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <h3>暂无解析结果</h3>
                    <p>上传简历文件即可开始解析</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Footer -->
    <footer class="footer">
        <p>简历解析工具 v1.0.0 - 预留 RAG 检索接口</p>
    </footer>
    
    <script>
        // State
        let resumes = [];
        
        // DOM Elements
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const langSelect = document.getElementById('langSelect');
        const modeSelect = document.getElementById('modeSelect');
        const resultsGrid = document.getElementById('resultsGrid');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const toastContainer = document.getElementById('toastContainer');
        
        // Event Listeners
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
        
        // Handle File Upload
        async function handleFiles(files) {
            if (files.length === 0) return;
            
            showLoading();
            
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.results) {
                    const successful = data.results.filter(r => r.success);
                    const failed = data.results.filter(r => !r.success);
                    
                    successful.forEach(result => {
                        resumes.push(result);
                    });
                    
                    renderResults();
                    updateStats();
                    
                    if (successful.length > 0) {
                        showToast(`成功解析 ${successful.length} 个简历`, 'success');
                    }
                    
                    if (failed.length > 0) {
                        failed.forEach(f => {
                            showToast(`${f.file_name}: ${f.error}`, 'error');
                        });
                    }
                }
            } catch (error) {
                showToast('上传失败: ' + error.message, 'error');
            } finally {
                hideLoading();
            }
        }
        
        // Render Results
        function renderResults() {
            if (resumes.length === 0) {
                resultsGrid.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">📭</div>
                        <h3>暂无解析结果</h3>
                        <p>上传简历文件即可开始解析</p>
                    </div>
                `;
                return;
            }
            
            resultsGrid.innerHTML = resumes.map((resume, index) => `
                <div class="resume-card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="file-icon">${getFileIcon(resume.file_type)}</div>
                            <div class="file-info">
                                <h3>${escapeHtml(resume.file_name)}</h3>
                                <span>${resume.file_type.toUpperCase()} · ${resume.parsed_at ? new Date(resume.parsed_at).toLocaleString() : ''}</span>
                            </div>
                        </div>
                        <div class="card-actions">
                            <button class="action-btn" onclick="toggleCard(this)" title="展开/收起">${resume._expanded ? '▼' : '▶'}</button>
                            <button class="action-btn" onclick="deleteResume(${index})" title="删除">🗑️</button>
                        </div>
                    </div>
                    <div class="card-body" style="display: ${resume._expanded ? 'block' : 'none'}">
                        ${resume.sections && resume.sections.length > 0 ? resume.sections.map(section => `
                            <div class="section-item">
                                <div class="section-header-item">
                                    <span class="section-tag ${getSectionClass(section.title)}">${escapeHtml(section.title)}</span>
                                    <span class="section-confidence">${Math.round(section.confidence * 100)}%</span>
                                </div>
                                <div class="section-content">${escapeHtml(section.content)}</div>
                            </div>
                        `).join('') : '<p style="color: var(--text-tertiary);">暂无章节信息</p>'}
                    </div>
                </div>
            `).join('');
            
            document.getElementById('resultCount').textContent = resumes.length;
        }
        
        function toggleCard(btn) {
            const card = btn.closest('.resume-card');
            const body = card.querySelector('.card-body');
            const isHidden = body.style.display === 'none';
            body.style.display = isHidden ? 'block' : 'none';
            btn.textContent = isHidden ? '▼' : '▶';
        }
        
        function deleteResume(index) {
            resumes.splice(index, 1);
            renderResults();
            updateStats();
            showToast('已删除简历', 'success');
        }
        
        function clearAll() {
            if (resumes.length === 0) return;
            if (confirm('确定要清空所有简历吗？')) {
                resumes = [];
                fetch('/api/resumes', { method: 'DELETE' });
                renderResults();
                updateStats();
                showToast('已清空全部', 'success');
            }
        }
        
        function updateStats() {
            document.getElementById('totalResumes').textContent = resumes.length;
            document.getElementById('totalSections').textContent = resumes.reduce((sum, r) => sum + (r.sections ? r.sections.length : 0), 0);
        }
        
        // Search
        async function searchResumes() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) return;
            
            showLoading();
            
            try {
                const response = await fetch(`/api/rag/search?q=${encodeURIComponent(query)}&top_k=10`);
                const data = await response.json();
                
                if (data.results && data.results.length > 0) {
                    resultsGrid.innerHTML = `
                        <div style="grid-column: 1/-1; margin-bottom: 20px;">
                            <h3 style="color: var(--text-secondary); font-size: 14px;">搜索 "${escapeHtml(query)}" 结果 (${data.results.length})</h3>
                        </div>
                        ${data.results.map(r => `
                            <div class="resume-card">
                                <div class="card-header">
                                    <div class="card-title">
                                        <div class="file-icon">🔍</div>
                                        <div class="file-info">
                                            <h3>${escapeHtml(r.resume_id)}</h3>
                                            <span>相关度: ${Math.round(r.score * 100)}%</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="card-body">
                                    <div class="section-item">
                                        <div class="section-header-item">
                                            <span class="section-tag">${escapeHtml(r.title)}</span>
                                        </div>
                                        <div class="section-content">${escapeHtml(r.content)}</div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    `;
                } else {
                    showToast('未找到相关结果', 'error');
                }
            } catch (error) {
                showToast('搜索失败: ' + error.message, 'error');
            } finally {
                hideLoading();
            }
        }
        
        // Utility Functions
        function getFileIcon(type) {
            const icons = {
                'image': '🖼️',
                'pdf': '📄',
                'docx': '📝',
                'doc': '📝'
            };
            return icons[type] || '📋';
        }
        
        function getSectionClass(title) {
            const t = title.toLowerCase();
            if (t.includes('教育')) return 'education';
            if (t.includes('工作') || t.includes('经历')) return 'experience';
            if (t.includes('技能') || t.includes('特长')) return 'skills';
            return '';
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function showLoading() {
            loadingOverlay.classList.add('active');
        }
        
        function hideLoading() {
            loadingOverlay.classList.remove('active');
        }
        
        function showToast(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                <span class="toast-icon">${type === 'success' ? '✅' : '❌'}</span>
                <span class="toast-message">${message}</span>
            `;
            toastContainer.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'slideIn 0.3s ease reverse';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
        
        // Initial render
        renderResults();
        updateStats();
    </script>
</body>
</html>
"""
