"""
自动识别解析器
"""

import sys
import time
import json
import argparse
from pathlib import Path
from typing import Union, List, Optional, Dict
from dataclasses import dataclass, field

# 确保项目根目录在 Python 路径中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from parser.base import BaseParser
from parser.image_parser import ImageParser
from parser.pdf_parser import PDFParser
from parser.docx_parser import DOCXParser, DOCParser
from models.resume import Resume
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParseCacheEntry:
    """解析缓存条目"""
    resume: Resume
    file_mtime: float
    file_size: int
    parse_time: float
    cached_at: float = field(default_factory=time.time)


class AutoDetectParser:
    """
    自动识别文件类型并路由到对应解析器
    
    特性:
    - 自动检测文件类型
    - 解析器缓存（避免重复创建）
    - 文件变化检测（mtime/size）
    - 批量处理支持
    """
    
    PARSER_MAP = {
        ".jpg": ImageParser,
        ".jpeg": ImageParser,
        ".png": ImageParser,
        ".bmp": ImageParser,
        ".webp": ImageParser,
        ".tiff": ImageParser,
        ".tif": ImageParser,
        ".pdf": PDFParser,
        ".docx": DOCXParser,
        ".doc": DOCParser
    }
    
    def __init__(
        self,
        default_lang: str = "ch",
        default_mode: str = "text",
        use_cache: bool = True,
        cache_ttl: int = 3600,
        **parser_kwargs
    ):
        """
        初始化解析器
        
        Args:
            default_lang: 默认语言 (ch/en/chinese_cht/japan/korean)
            default_mode: PDF解析模式 (text/ocr)
            use_cache: 是否启用解析缓存
            cache_ttl: 缓存有效期（秒）
            **parser_kwargs: 传递给解析器的额外参数
        """
        self.default_lang = default_lang
        self.default_mode = default_mode
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.parser_kwargs = parser_kwargs
        self._parsers: Dict[str, BaseParser] = {}
        self._cache: Dict[str, ParseCacheEntry] = {}
        self._stats = {
            "total_parses": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def _get_parser(self, file_path: Union[str, Path]) -> BaseParser:
        """获取或创建解析器实例"""
        path = Path(file_path)
        ext = path.suffix.lower()
        parser_class = self.PARSER_MAP.get(ext)
        
        if parser_class is None:
            raise ValueError(f"不支持的文件类型: {ext}")
        
        # 构建缓存键
        cache_key = f"{ext}_{self.default_lang}_{self.default_mode}"
        
        if cache_key not in self._parsers:
            logger.debug(f"创建新解析器: {parser_class.__name__} (key={cache_key})")
            if parser_class == ImageParser:
                self._parsers[cache_key] = parser_class(
                    lang=self.default_lang,
                    **self.parser_kwargs
                )
            elif parser_class == PDFParser:
                self._parsers[cache_key] = parser_class(
                    mode=self.default_mode,
                    lang=self.default_lang,
                    **self.parser_kwargs
                )
            elif parser_class in (DOCXParser, DOCParser):
                self._parsers[cache_key] = parser_class()
            else:
                self._parsers[cache_key] = parser_class()
        
        return self._parsers[cache_key]
    
    def _get_cache_key(self, file_path: Path) -> str:
        """生成缓存键"""
        return f"{file_path.absolute()}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
    
    def _is_cache_valid(self, file_path: Path, entry: ParseCacheEntry) -> bool:
        """检查缓存是否有效"""
        if not self.use_cache:
            return False
        
        # 检查 TTL
        if time.time() - entry.cached_at > self.cache_ttl:
            return False
        
        # 检查文件是否变化
        stat = file_path.stat()
        return stat.st_mtime == entry.file_mtime and stat.st_size == entry.file_size
    
    def _clear_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if current_time - v.cached_at > self.cache_ttl
        ]
        for k in expired_keys:
            del self._cache[k]
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存")
    
    def parse(self, file_path: Union[str, Path]) -> Resume:
        """
        解析简历文件
        
        Args:
            file_path: 简历文件路径
            
        Returns:
            Resume: 解析后的简历对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件无效或不支持
        """
        path = Path(file_path)
        
        # 文件验证
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not path.is_file():
            raise ValueError(f"不是有效的文件: {file_path}")
        
        ext = path.suffix.lower()
        logger.info(f"检测到文件类型: {ext} ({path.name})")
        
        # 检查缓存
        cache_key = self._get_cache_key(path)
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if self._is_cache_valid(path, entry):
                self._stats["cache_hits"] += 1
                logger.debug(f"缓存命中: {path.name}")
                return entry.resume
        
        self._stats["cache_misses"] += 1
        
        # 解析文件
        start_time = time.time()
        parser = self._get_parser(path)
        resume = parser.parse(path)
        
        # 更新缓存
        if self.use_cache:
            stat = path.stat()
            self._cache[cache_key] = ParseCacheEntry(
                resume=resume,
                file_mtime=stat.st_mtime,
                file_size=stat.st_size,
                parse_time=time.time() - start_time
            )
            self._clear_expired_cache()
        
        self._stats["total_parses"] += 1
        logger.info(f"解析完成: {path.name} (耗时: {time.time() - start_time:.2f}s)")
        
        return resume
    
    def invalidate_cache(self, file_path: Optional[Union[str, Path]] = None):
        """
        使缓存失效
        
        Args:
            file_path: 特定文件路径，为None则清除所有缓存
        """
        if file_path:
            path = Path(file_path)
            cache_key = self._get_cache_key(path)
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"清除缓存: {path.name}")
        else:
            self._cache.clear()
            logger.debug("清除所有缓存")
    
    def parse_batch(
        self,
        file_paths: List[Union[str, Path]],
        stop_on_error: bool = False
    ) -> List[Resume]:
        """
        批量解析简历
        
        Args:
            file_paths: 文件路径列表
            stop_on_error: 遇到错误是否停止
            
        Returns:
            List[Resume]: 解析结果列表
        """
        results = []
        for file_path in file_paths:
            try:
                resume = self.parse(file_path)
                results.append(resume)
            except Exception as e:
                logger.error(f"解析失败 {file_path}: {e}")
                if stop_on_error:
                    raise
                results.append(Resume(
                    file_name=str(file_path),
                    file_type="error",
                    metadata={"error": str(e)}
                ))
        return results
    
    def get_stats(self) -> Dict:
        """获取解析统计信息"""
        total = self._stats["cache_hits"] + self._stats["cache_misses"]
        hit_rate = self._stats["cache_hits"] / total if total > 0 else 0
        return {
            **self._stats,
            "cache_hit_rate": round(hit_rate, 2),
            "cached_files": len(self._cache),
            "active_parsers": len(self._parsers)
        }
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """获取支持的文件扩展名"""
        return list(cls.PARSER_MAP.keys())
    
    @staticmethod
    def is_supported(file_path: Union[str, Path]) -> bool:
        """检查是否支持此文件"""
        ext = Path(file_path).suffix.lower()
        return ext in AutoDetectParser.PARSER_MAP


def _parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="简历文件解析器 - 支持图片、PDF、Word 格式",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("file", help="简历文件路径")
    parser.add_argument("-o", "--output", help="输出 JSON 文件路径")
    parser.add_argument("--format", choices=["json", "text", "markdown"], default="text", help="输出格式")
    parser.add_argument("--mode", choices=["text", "ocr"], default="text", help="PDF 解析模式")
    parser.add_argument("--lang", choices=["ch", "en", "chinese_cht", "japan", "korean"], default="ch", help="OCR 语言")
    parser.add_argument("--no-cache", action="store_true", help="禁用缓存")
    return parser.parse_args()


def _print_resume(resume: Resume, format_type: str):
    """格式化输出简历"""
    if format_type == "json":
        print(json.dumps(resume.to_dict(), ensure_ascii=False, indent=2))
    elif format_type == "markdown":
        print(f"\n# 简历解析结果: {resume.file_name}\n")
        print(f"**类型**: {resume.file_type}\n**解析时间**: {resume.parsed_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        for section in resume.sections:
            confidence_str = f" *(置信度: {section.confidence:.0%})*" if section.confidence < 1.0 else ""
            print(f"## {section.title}{confidence_str}\n{section.content}\n")
    else:
        print("\n" + "=" * 60)
        print(f"📄 简历解析结果: {resume.file_name}")
        print(f"📅 解析时间: {resume.parsed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 类型: {resume.file_type}")
        print("=" * 60 + "\n")
        for section in resume.sections:
            print(f"【{section.title}】")
            print(f"   {section.content}")
            if section.confidence < 1.0:
                print(f"   (置信度: {section.confidence:.0%})")
            print()


def main():
    """命令行入口函数"""
    args = _parse_arguments()
    
    # 创建解析器
    parser = AutoDetectParser(
        default_lang=args.lang,
        default_mode=args.mode,
        use_cache=not args.no_cache
    )
    
    # 解析文件
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"错误: 文件不存在: {file_path}")
        return 1
    
    try:
        resume = parser.parse(file_path)
        _print_resume(resume, args.format)
        
        # 如果指定了输出文件，保存 JSON
        if args.output and args.format == "json":
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(resume.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {output_path}")
        
        return 0
    except Exception as e:
        print(f"解析失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
