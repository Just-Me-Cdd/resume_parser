#!/usr/bin/env python3
"""
简历解析工具 - 主入口
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from models.resume import Resume
from parser.auto_detect import AutoDetectParser
from storage.rag_retriever import RAGRetriever
from utils.logger import setup_logger, loguru_logger

logger = setup_logger("resume_parser")


def parse_args():
    parser = argparse.ArgumentParser(description="简历解析工具 - 支持图片、PDF、Word 格式", formatter_class=argparse.RawDescriptionHelpFormatter, epilog="示例:\n  %(prog)s resume.jpg\n  %(prog)s resume.pdf -o result.json\n  %(prog)s resume.jpg --mode ocr\n  %(prog)s --batch ./resumes/")
    parser.add_argument("file", nargs="?", help="简历文件路径")
    parser.add_argument("-o", "--output", help="输出 JSON 文件路径")
    parser.add_argument("--format", choices=["json", "text", "markdown"], default="text", help="输出格式")
    parser.add_argument("--mode", choices=["text", "ocr"], default="text", help="PDF 解析模式")
    parser.add_argument("--lang", choices=["ch", "en", "chinese_cht", "japan", "korean"], default="ch", help="OCR 语言")
    parser.add_argument("--batch", help="批量处理目录")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("--rag", action="store_true", help="启用 RAG 模式（预留）")
    parser.add_argument("--vector-store", choices=["simple", "chroma"], default="simple", help="向量存储类型")
    parser.add_argument("--no-preprocess", action="store_true", help="禁用图片预处理")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")
    return parser.parse_args()


def print_resume_text(resume: Resume):
    print("\n" + "=" * 60)
    print(f"📄 简历解析结果: {resume.file_name}")
    print(f"📅 解析时间: {resume.parsed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 类型: {resume.file_type}")
    print("=" * 60 + "\n")
    for i, section in enumerate(resume.sections, 1):
        print(f"【{i}. {section.title}】")
        print(f"   {section.content}")
        if section.confidence < 1.0:
            print(f"   (置信度: {section.confidence:.0%})")
        print()


def print_resume_markdown(resume: Resume):
    print(f"\n# 简历解析结果: {resume.file_name}\n")
    print(f"**类型**: {resume.file_type}\n**解析时间**: {resume.parsed_at.strftime('%Y-%m-%d %H:%M:%S')}\n**章节数**: {len(resume.sections)}\n---\n")
    for section in resume.sections:
        confidence_str = f" *(置信度: {section.confidence:.0%})*" if section.confidence < 1.0 else ""
        print(f"## {section.title}{confidence_str}\n{section.content}\n")


def save_resume_json(resume: Resume, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resume.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存: {output_path}")


def process_single_file(parser: AutoDetectParser, file_path: Path, args):
    try:
        resume = parser.parse(file_path)
        if args.format == "json" and args.output:
            save_resume_json(resume, Path(args.output))
        elif args.format == "text":
            print_resume_text(resume)
        elif args.format == "markdown":
            print_resume_markdown(resume)
        if args.rag:
            print_rag_info(resume)
        return resume
    except Exception as e:
        logger.error(f"解析失败: {file_path} - {e}")
        return None


def process_batch(parser: AutoDetectParser, directory: Path, args) -> list:
    logger.info(f"批量处理目录: {directory}")
    files = []
    for ext in AutoDetectParser.get_supported_extensions():
        if args.recursive:
            files.extend(directory.rglob(f"*{ext}"))
        else:
            files.extend(directory.glob(f"*{ext}"))
    
    if not files:
        logger.warning(f"目录中没有找到支持的简历文件: {directory}")
        return []
    
    logger.info(f"找到 {len(files)} 个简历文件")
    results = []
    success_count = 0
    fail_count = 0
    
    for file_path in files:
        logger.info(f"处理: {file_path.name}")
        resume = process_single_file(parser, file_path, args)
        if resume:
            results.append(resume)
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print("📊 批量处理统计")
    print("=" * 60)
    print(f"✅ 成功: {success_count}\n❌ 失败: {fail_count}\n📁 总计: {len(files)}")
    print("=" * 60 + "\n")
    return results


def print_rag_info(resume: Resume):
    print("\n" + "=" * 60)
    print("🔮 RAG 接口预留信息")
    print("=" * 60)
    rag_data = resume.to_rag_format()
    print(f"共 {len(rag_data)} 个检索单元\n示例检索代码:")
    print("```python")
    print("from storage.rag_retriever import RAGRetriever")
    print("retriever = RAGRetriever(store_type='simple')")
    print("retriever.add_resume(resume)")
    print("results = retriever.retrieve('Python开发经验')")
    print("```")
    print("=" * 60 + "\n")


def print_supported_formats():
    formats = {"图片": [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"], "PDF": [".pdf"], "Word": [".docx", ".doc"]}
    print("\n支持的格式:")
    for name, exts in formats.items():
        print(f"  {name}: {', '.join(exts)}")
    print()


def main():
    args = parse_args()
    if args.verbose:
        import logging
        logger.setLevel(logging.DEBUG)
    print_supported_formats()
    
    parser_kwargs = {}
    if hasattr(args, 'no_preprocess') and args.no_preprocess:
        parser_kwargs["use_preprocessing"] = False
    
    parser = AutoDetectParser(default_lang=args.lang, default_mode=args.mode, **parser_kwargs)
    
    if args.batch:
        directory = Path(args.batch)
        if not directory.exists():
            logger.error(f"目录不存在: {directory}")
            return 1
        process_batch(parser, directory, args)
        return 0
    
    if not args.file:
        logger.error("请提供简历文件路径，或使用 --batch 指定目录")
        return 1
    
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        return 1
    
    process_single_file(parser, file_path, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
