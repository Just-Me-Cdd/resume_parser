"""
日志工具模块
"""

import logging
import sys
from pathlib import Path
from loguru import logger as loguru_logger

# 移除默认 handler
loguru_logger.remove()

# 添加控制台输出
loguru_logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


def setup_logger(
    name: str = "resume_parser",
    log_file: str = None,
    level: str = "INFO"
) -> logging.Logger:
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（可选）
        level: 日志级别
    
    Returns:
        配置好的 logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件 handler（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "resume_parser") -> logging.Logger:
    """
    获取 logger 实例（使用 loguru）
    
    Args:
        name: 模块名称
    
    Returns:
        logger 实例
    """
    return logging.getLogger(name)
