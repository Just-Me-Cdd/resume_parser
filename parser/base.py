"""
解析器基类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
from models.resume import Resume
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseParser(ABC):
    """解析器抽象基类"""
    SUPPORTED_EXTENSIONS: list = []
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> Resume:
        """解析简历文件"""
        pass
    
    @classmethod
    def can_parse(cls, file_path: Union[str, Path]) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS
    
    def validate_file(self, file_path: Union[str, Path]) -> Path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not path.is_file():
            raise ValueError(f"不是有效的文件: {file_path}")
        if not self.can_parse(path):
            raise ValueError(f"不支持的文件类型: {path.suffix}")
        return path
    
    def get_file_info(self, file_path: Path) -> dict:
        stat = file_path.stat()
        return {"name": file_path.name, "size": stat.st_size, "extension": file_path.suffix.lower(), "modified": stat.st_mtime}
