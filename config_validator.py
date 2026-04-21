"""
配置验证模块
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ConfigLevel(Enum):
    """配置级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ConfigIssue:
    """配置问题"""
    level: ConfigLevel
    key: str
    message: str
    suggestion: Optional[str] = None


class ConfigValidator:
    """
    配置验证器
    
    验证配置文件的完整性和有效性
    """
    
    SUPPORTED_LANGS = ["ch", "en", "chinese_cht", "japan", "korean"]
    SUPPORTED_MODES = ["text", "ocr"]
    SUPPORTED_IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"]
    SUPPORTED_DOC_EXTS = [".pdf", ".docx", ".doc"]
    
    def __init__(self, config_module=None):
        """
        初始化验证器
        
        Args:
            config_module: 配置模块，如果为None则导入config
        """
        self.config_module = config_module
        self.issues: List[ConfigIssue] = []
    
    def _load_config(self):
        """加载配置模块"""
        if self.config_module is None:
            import config
            self.config_module = config
        return self.config_module
    
    def validate_all(self) -> Tuple[bool, List[ConfigIssue]]:
        """
        执行所有验证
        
        Returns:
            (是否通过, 问题列表)
        """
        self.issues = []
        self._validate_ocr_config()
        self._validate_preprocess_config()
        self._validate_section_patterns()
        self._validate_file_extensions()
        self._validate_environment()
        
        has_errors = any(i.level == ConfigLevel.ERROR for i in self.issues)
        return not has_errors, self.issues
    
    def _add_issue(self, level: ConfigLevel, key: str, message: str, suggestion: str = None):
        """添加问题"""
        self.issues.append(ConfigIssue(
            level=level,
            key=key,
            message=message,
            suggestion=suggestion
        ))
    
    def _validate_ocr_config(self):
        """验证OCR配置"""
        config = self._load_config()
        ocr = config.OCR_CONFIG
        
        # 验证语言
        lang = ocr.get("lang", "")
        if lang not in self.SUPPORTED_LANGS:
            self._add_issue(
                ConfigLevel.WARNING,
                "OCR_CONFIG.lang",
                f"不支持的OCR语言: {lang}",
                f"建议使用: {', '.join(self.SUPPORTED_LANGS)}"
            )
        
        # 验证布尔值
        if not isinstance(ocr.get("use_angle_cls", True), bool):
            self._add_issue(
                ConfigLevel.ERROR,
                "OCR_CONFIG.use_angle_cls",
                "use_angle_cls 必须是布尔值"
            )
        
        # 验证阈值范围
        for key in ["det_db_thresh", "det_db_box_thresh"]:
            value = ocr.get(key, 0)
            if not (0 <= value <= 1):
                self._add_issue(
                    ConfigLevel.ERROR,
                    f"OCR_CONFIG.{key}",
                    f"{key} 必须在 0-1 范围内，当前值: {value}"
                )
    
    def _validate_preprocess_config(self):
        """验证预处理配置"""
        config = self._load_config()
        prep = config.PREPROCESS_CONFIG
        
        # 验证去噪强度
        denoise_h = prep.get("denoise_h", 10)
        if not (1 <= denoise_h <= 20):
            self._add_issue(
                ConfigLevel.WARNING,
                "PREPROCESS_CONFIG.denoise_h",
                f"denoise_h 建议在 1-20 范围内，当前值: {denoise_h}",
                "过大可能导致图像模糊，过小可能去噪效果不佳"
            )
        
        # 验证CLAHE参数
        clip_limit = prep.get("clahe_clip_limit", 2.0)
        if not (0.1 <= clip_limit <= 10):
            self._add_issue(
                ConfigLevel.WARNING,
                "PREPROCESS_CONFIG.clahe_clip_limit",
                f"clahe_clip_limit 建议在 0.1-10 范围内，当前值: {clip_limit}"
            )
        
        # 验证网格大小
        grid_size = prep.get("clahe_grid_size", (8, 8))
        if not isinstance(grid_size, tuple) or len(grid_size) != 2:
            self._add_issue(
                ConfigLevel.ERROR,
                "PREPROCESS_CONFIG.clahe_grid_size",
                "clahe_grid_size 必须是二元元组，如 (8, 8)"
            )
    
    def _validate_section_patterns(self):
        """验证章节模式"""
        config = self._load_config()
        patterns = config.SECTION_PATTERNS
        
        if not patterns:
            self._add_issue(
                ConfigLevel.ERROR,
                "SECTION_PATTERNS",
                "SECTION_PATTERNS 不能为空"
            )
            return
        
        # 检查是否有重复标题
        titles = [p[1] for p in patterns]
        if len(titles) != len(set(titles)):
            self._add_issue(
                ConfigLevel.WARNING,
                "SECTION_PATTERNS",
                "SECTION_PATTERNS 中存在重复的标题"
            )
        
        # 验证正则表达式
        import re
        for pattern, title in patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                self._add_issue(
                    ConfigLevel.ERROR,
                    f"SECTION_PATTERNS['{title}']",
                    f"无效的正则表达式: {pattern}",
                    str(e)
                )
    
    def _validate_file_extensions(self):
        """验证文件扩展名"""
        config = self._load_config()
        
        all_exts = (
            config.SUPPORTED_IMAGE_EXTENSIONS +
            config.SUPPORTED_PDF_EXTENSIONS +
            config.SUPPORTED_DOCX_EXTENSIONS
        )
        
        # 检查格式
        for ext in all_exts:
            if not ext.startswith("."):
                self._add_issue(
                    ConfigLevel.ERROR,
                    f"SUPPORTED_*_EXTENSIONS",
                    f"扩展名必须以 '.' 开头: {ext}"
                )
        
        # 检查重复
        if len(all_exts) != len(set(all_exts)):
            self._add_issue(
                ConfigLevel.WARNING,
                "SUPPORTED_*_EXTENSIONS",
                "存在重复的扩展名配置"
            )
    
    def _validate_environment(self):
        """验证环境变量"""
        # 检查关键环境变量
        env_checks = [
            ("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", False),
        ]
        
        for var, should_exist in env_checks:
            if should_exist and not os.environ.get(var):
                self._add_issue(
                    ConfigLevel.INFO,
                    f"ENV[{var}]",
                    f"建议设置环境变量 {var}=True 以提升启动速度"
                )
    
    def get_report(self) -> str:
        """生成验证报告"""
        if not self.issues:
            return "✅ 配置验证通过！"
        
        lines = []
        errors = [i for i in self.issues if i.level == ConfigLevel.ERROR]
        warnings = [i for i in self.issues if i.level == ConfigLevel.WARNING]
        infos = [i for i in self.issues if i.level == ConfigLevel.INFO]
        
        if errors:
            lines.append(f"\n❌ 错误 ({len(errors)}):")
            for i in errors:
                lines.append(f"   • {i.key}: {i.message}")
                if i.suggestion:
                    lines.append(f"     建议: {i.suggestion}")
        
        if warnings:
            lines.append(f"\n⚠️  警告 ({len(warnings)}):")
            for i in warnings:
                lines.append(f"   • {i.key}: {i.message}")
        
        if infos:
            lines.append(f"\nℹ️  提示 ({len(infos)}):")
            for i in infos:
                lines.append(f"   • {i.message}")
        
        return "\n".join(lines)


def validate_config() -> Tuple[bool, List[ConfigIssue]]:
    """
    便捷函数：验证配置
    
    Returns:
        (是否通过, 问题列表)
    """
    validator = ConfigValidator()
    return validator.validate_all()


def print_validation_report():
    """打印验证报告"""
    validator = ConfigValidator()
    passed, issues = validator.validate_all()
    
    print("\n" + "=" * 50)
    print("📋 配置验证报告")
    print("=" * 50)
    
    if passed:
        print("✅ 所有验证通过！")
    else:
        print(validator.get_report())
    
    print("=" * 50 + "\n")
    
    return passed


if __name__ == "__main__":
    print_validation_report()
