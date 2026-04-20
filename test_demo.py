#!/usr/bin/env python3
"""
简历解析工具 - 测试脚本
"""

import sys
from pathlib import Path


def test_imports():
    print("=" * 50)
    print("测试模块导入...")
    print("=" * 50)
    
    modules = [("pydantic", "数据模型"), ("loguru", "日志"), ("PIL", "图片处理"), ("cv2", "OpenCV"), ("fitz", "PyMuPDF"), ("docx", "python-docx")]
    all_ok = True
    for module, desc in modules:
        try:
            __import__(module)
            print(f"✅ {module:15} - {desc}")
        except ImportError as e:
            print(f"❌ {module:15} - {desc} - 未安装: {e}")
            all_ok = False
    
    try:
        from paddleocr import PaddleOCR
        print(f"✅ paddleocr        - PaddleOCR")
    except ImportError as e:
        print(f"⚠️ paddleocr        - 未安装: {e}")
    
    print()
    return all_ok


def test_parsers():
    print("=" * 50)
    print("测试解析器模块...")
    print("=" * 50)
    try:
        from parser.auto_detect import AutoDetectParser
        print("✅ 所有解析器模块导入成功")
        print(f"✅ 支持的文件类型: {AutoDetectParser.get_supported_extensions()}")
        return True
    except ImportError as e:
        print(f"❌ 解析器模块导入失败: {e}")
        return False


def test_models():
    print()
    print("=" * 50)
    print("测试数据模型...")
    print("=" * 50)
    try:
        from models.resume import Resume, ResumeSection
        section = ResumeSection(title="姓名", content="张三", confidence=0.95)
        resume = Resume(sections=[section], raw_text="张三", file_name="test.jpg", file_type="image")
        assert resume.get_section("姓名").content == "张三"
        print("✅ ResumeSection 创建成功")
        json_data = resume.to_dict()
        assert "sections" in json_data
        print("✅ Resume.to_dict() 工作正常")
        return True
    except ImportError as e:
        print(f"❌ 数据模型导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    print()
    print("=" * 60)
    print("🧪 简历解析工具 - 安装测试")
    print("=" * 60)
    
    results = []
    results.append(("模块导入", test_imports()))
    results.append(("解析器", test_parsers()))
    results.append(("数据模型", test_models()))
    
    print()
    print("=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过！可以开始使用简历解析工具。")
        print("\n使用示例:")
        print("  python main.py resume.jpg")
        print("  python main.py resume.pdf -o result.json")
        return 0
    else:
        print("\n⚠️ 部分测试未通过，请检查依赖安装。")
        print("\n安装命令:")
        print("  pip install -r requirements.txt")
        print("  pip install paddlepaddle paddleocr")
        return 1


if __name__ == "__main__":
    sys.exit(main())
