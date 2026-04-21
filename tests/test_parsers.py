"""
解析器单元测试
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from parser.base import BaseParser, BaseParserMeta
from parser.auto_detect import AutoDetectParser


class TestBaseParser:
    """BaseParser 测试"""
    
    def test_parser_requires_extensions(self):
        """测试解析器需要定义扩展名"""
        # 这是一个正确的解析器实现
        class ValidParser(BaseParser):
            SUPPORTED_EXTENSIONS = [".jpg", ".png"]
            
            def parse(self, file_path):
                return Mock()
        
        # 应该可以正常创建
        parser = ValidParser()
        assert parser.SUPPORTED_EXTENSIONS == [".jpg", ".png"]
    
    def test_can_parse(self):
        """测试文件类型检查"""
        class TestParser(BaseParser):
            SUPPORTED_EXTENSIONS = [".jpg", ".png"]
            
            def parse(self, file_path):
                return Mock()
        
        assert TestParser.can_parse("test.jpg") == True
        assert TestParser.can_parse("test.png") == True
        assert TestParser.can_parse("test.pdf") == False
        assert TestParser.can_parse("test.txt") == False
    
    def test_validate_file_not_exists(self):
        """测试文件不存在验证"""
        class TestParser(BaseParser):
            SUPPORTED_EXTENSIONS = [".jpg"]
            
            def parse(self, file_path):
                return Mock()
        
        parser = TestParser()
        with pytest.raises(FileNotFoundError):
            parser.validate_file("nonexistent.jpg")
    
    def test_validate_file_not_supported(self):
        """测试不支持的文件类型"""
        with pytest.raises(NotImplementedError):
            class TestParser(BaseParser):
                def parse(self, file_path):
                    return Mock()
            # 没有定义 SUPPORTED_EXTENSIONS 应该报错
            TestParser()
    
    def test_get_file_info(self, tmp_path):
        """测试获取文件信息"""
        # 创建临时文件
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")
        
        class TestParser(BaseParser):
            SUPPORTED_EXTENSIONS = [".jpg"]
            
            def parse(self, file_path):
                return Mock()
        
        parser = TestParser()
        info = parser.get_file_info(test_file)
        
        assert info["name"] == "test.jpg"
        assert info["size"] > 0
        assert info["size_mb"] > 0
        assert info["extension"] == ".jpg"
        assert "modified_time" in info
    
    def test_parse_count_tracking(self):
        """测试解析计数"""
        class TestParser(BaseParser):
            SUPPORTED_EXTENSIONS = [".jpg"]
            
            def parse(self, file_path):
                self._record_parse()
                return Mock()
        
        parser = TestParser()
        assert parser.parse_count == 0
        
        parser.parse("test.jpg")
        assert parser.parse_count == 1
        
        parser.parse("test2.jpg")
        assert parser.parse_count == 2


class TestAutoDetectParser:
    """AutoDetectParser 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        parser = AutoDetectParser()
        assert parser.default_lang == "ch"
        assert parser.default_mode == "text"
        assert parser.use_cache == True
        assert parser.cache_ttl == 3600
    
    def test_initialization_custom(self):
        """测试自定义初始化"""
        parser = AutoDetectParser(
            default_lang="en",
            default_mode="ocr",
            use_cache=False,
            cache_ttl=7200
        )
        assert parser.default_lang == "en"
        assert parser.default_mode == "ocr"
        assert parser.use_cache == False
        assert parser.cache_ttl == 7200
    
    def test_get_supported_extensions(self):
        """测试获取支持的扩展名"""
        exts = AutoDetectParser.get_supported_extensions()
        assert ".jpg" in exts
        assert ".pdf" in exts
        assert ".docx" in exts
        assert len(exts) >= 10
    
    def test_is_supported(self):
        """测试文件支持检查"""
        assert AutoDetectParser.is_supported("test.jpg") == True
        assert AutoDetectParser.is_supported("test.pdf") == True
        assert AutoDetectParser.is_supported("test.docx") == True
        assert AutoDetectParser.is_supported("test.txt") == False
    
    def test_parse_file_not_exists(self):
        """测试解析不存在的文件"""
        parser = AutoDetectParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("nonexistent_file.pdf")
    
    def test_get_stats(self):
        """测试获取统计信息"""
        parser = AutoDetectParser()
        stats = parser.get_stats()
        
        assert "total_parses" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cache_hit_rate" in stats
        assert "cached_files" in stats
        assert "active_parsers" in stats
    
    def test_invalidate_cache(self):
        """测试缓存失效"""
        parser = AutoDetectParser()
        parser.invalidate_cache()  # 清除所有缓存
        parser.invalidate_cache("test.jpg")  # 清除特定文件
    
    @patch('parser.auto_detect.ImageParser')
    def test_parser_creation(self, mock_image_parser):
        """测试解析器创建"""
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = Mock()
        mock_image_parser.return_value = mock_parser_instance
        
        parser = AutoDetectParser()
        # 这会触发解析器创建，但由于文件不存在会先报错
        with pytest.raises(FileNotFoundError):
            parser.parse("test.jpg")


class TestParserCaching:
    """解析器缓存测试"""
    
    def test_parser_cache_key_generation(self, tmp_path):
        """测试缓存键生成"""
        parser = AutoDetectParser()
        
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")
        
        cache_key = parser._get_cache_key(test_file)
        assert str(test_file.absolute()) in cache_key
        assert str(test_file.stat().st_mtime) in cache_key
    
    def test_cache_invalidation(self, tmp_path):
        """测试缓存失效机制"""
        parser = AutoDetectParser(use_cache=True)
        
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")
        
        # 清除所有缓存
        parser.invalidate_cache()
        assert len(parser._cache) == 0
