"""
文本清洗器
"""

import re
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class TextCleaner:
    """简历文本清洗器"""
    
    def __init__(self):
        self.char_replacements = {
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
            '\u2014': '-', '\u2013': '-', '\u00a0': ' ', '\u3000': ' ', '\t': ' ',
        }
    
    def clean(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        
        cleaned = text
        for old, new in self.char_replacements.items():
            cleaned = cleaned.replace(old, new)
        cleaned = self._normalize_whitespace(cleaned)
        cleaned = self._remove_control_chars(cleaned)
        cleaned = self._normalize_punctuation(cleaned)
        return cleaned.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r' +', ' ', text)
        text = re.sub(r' *\n *', '\n', text)
        text = re.sub(r'[ \t]+\n', '\n', text)
        text = re.sub(r'\n[ \t]+', '\n', text)
        return text
    
    def _remove_control_chars(self, text: str) -> str:
        control_chars = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
        return control_chars.sub('', text)
    
    def _normalize_punctuation(self, text: str) -> str:
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'\u2026', '...', text)
        text = re.sub(r'[-=_]{2,}', '-', text)
        text = re.sub(r',\s*([^\s,])', r', \1', text)
        text = re.sub(r'\s*,', ',', text)
        return text
    
    def clean_name(self, text: str) -> str:
        if not text:
            return ""
        prefixes = [r'^姓名[：:]\s*', r'^Name\s*[:]\s*', r'^\s*']
        for prefix in prefixes:
            text = re.sub(prefix, '', text, flags=re.I)
        return self.clean(text)
    
    def clean_phone(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r'[^\d\s\-()+]', '', text)
        cleaned = re.sub(r'[-]+', '-', cleaned)
        return cleaned.strip()
    
    def clean_email(self, text: str) -> str:
        if not text:
            return ""
        prefixes = [r'^邮箱[：:]\s*', r'^Email\s*[:]\s*', r'^E-mail\s*[:]\s*']
        for prefix in prefixes:
            text = re.sub(prefix, '', text, flags=re.I)
        cleaned = re.sub(r'[^\w@.\-]', '', text)
        return cleaned.strip().lower()
    
    def clean_education(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'(\d{4})\s*[年\-~]\s*(\d{4})', r'\1-\2', text)
        text = re.sub(r'(\d{4})\s*[年\-~]\s*(今|现在|至今)', r'\1-至今', text)
        text = self._normalize_whitespace(text)
        return text
    
    def clean_work_experience(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'(\d{4})\s*[./\-]\s*(\d{1,2})\s*[./\-~\-]\s*(\d{4})\s*[./\-]\s*(\d{1,2})', r'\1-\2至\3-\4', text)
        text = re.sub(r'(职位|岗位)\s*[:：]\s*', '', text)
        text = re.sub(r'^[\-\*\•]\s*', '', text, flags=re.MULTILINE)
        return self._normalize_whitespace(text)
    
    def split_sentences(self, text: str) -> list:
        if not text:
            return []
        sentences = re.split(r'[。！？；\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def remove_noise(self, text: str) -> str:
        if not text:
            return ""
        noise_patterns = [r'第\s*\d+\s*页', r'Page\s*\d+', r'共\s*\d+\s*页', r'Copyright.*', r'版权所有.*']
        cleaned = text
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.I)
        return cleaned.strip()
