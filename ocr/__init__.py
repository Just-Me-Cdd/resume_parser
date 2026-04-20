"""
简历解析工具 - OCR 模块
"""

from ocr.base_ocr import BaseOCR
from ocr.paddle_ocr import PaddleOCREngine

_OCR_ENGINES = {"paddle": PaddleOCREngine}


def get_ocr_engine(engine: str = "paddle", **kwargs) -> BaseOCR:
    """获取 OCR 引擎实例"""
    engine_class = _OCR_ENGINES.get(engine.lower())
    if engine_class is None:
        supported = ", ".join(_OCR_ENGINES.keys())
        raise ValueError(f"不支持的 OCR 引擎: {engine}。支持的引擎: {supported}")
    return engine_class(**kwargs)


def register_ocr_engine(name: str, engine_class: type):
    """注册自定义 OCR 引擎"""
    _OCR_ENGINES[name.lower()] = engine_class


__all__ = ["BaseOCR", "PaddleOCREngine", "get_ocr_engine", "register_ocr_engine"]
