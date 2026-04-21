"""
解析器基类
"""

from abc import ABC, abstractmethod, ABCMeta
from pathlib import Path
from typing import Union, List
from models.resume import Resume
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseParserMeta(ABCMeta):
    """解析器元类 - 强制子类实现抽象方法"""
    
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls._validate_implementation(instance)
        return instance
    
    @classmethod
    def _validate_implementation(cls, instance):
        """验证子类是否正确实现了抽象方法"""
        if not hasattr(instance, 'SUPPORTED_EXTENSIONS') or not instance.SUPPORTED_EXTENSIONS:
            raise NotImplementedError(f"{instance.__class__.__name__} 必须定义 SUPPORTED_EXTENSIONS")


class BaseParser(ABC):
    """
    解析器抽象基类
    
    所有解析器必须:
    1. 定义 SUPPORTED_EXTENSIONS 类属性
    2. 实现 parse() 抽象方法
    3. 可选实现 can_parse() 类方法
    """
    __metaclass__ = BaseParserMeta
    
    SUPPORTED_EXTENSIONS: List[str] = []
    
    def __init__(self):
        self._parse_count = 0
        self._last_parse_time = None
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> Resume:
        """解析简历文件
        
        Args:
            file_path: 简历文件路径
            
        Returns:
            Resume: 解析后的简历对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或内容无效
        """
        pass
    
    @classmethod
    def can_parse(cls, file_path: Union[str, Path]) -> bool:
        """检查是否能够解析此文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 如果文件类型被支持返回 True
        """
        if not cls.SUPPORTED_EXTENSIONS:
            return False
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS
    
    def validate_file(self, file_path: Union[str, Path]) -> Path:
        """验证文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            Path: 验证通过的文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不是有效文件或不支持的类型
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not path.is_file():
            raise ValueError(f"不是有效的文件: {file_path}")
        if not self.can_parse(path):
            raise ValueError(f"不支持的文件类型: {path.suffix}，支持的类型: {', '.join(self.SUPPORTED_EXTENSIONS)}")
        return path
    
    def get_file_info(self, file_path: Path) -> dict:
        """获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 包含文件信息的字典
        """
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "extension": file_path.suffix.lower(),
            "modified": stat.st_mtime,
            "modified_time": stat.st_mtime
        }
    
    def _record_parse(self):
        """记录解析操作"""
        import time
        self._parse_count += 1
        self._last_parse_time = time.time()
    
    @property
    def parse_count(self) -> int:
        """获取解析次数"""
        return self._parse_count
