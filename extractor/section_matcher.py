"""
标题-内容配对器
"""

import re
from typing import List, Dict, Optional, Tuple
from config import SECTION_PATTERNS
from models.resume import ResumeSection
from extractor.cleaner import TextCleaner
from utils.logger import get_logger

logger = get_logger(__name__)


class SectionMatcher:
    """标题-内容配对引擎"""
    
    def __init__(self, patterns: Optional[List[Tuple[str, str]]] = None, confidence_threshold: float = 0.5):
        self.patterns = patterns or SECTION_PATTERNS
        self.confidence_threshold = confidence_threshold
        self._compile_patterns()
        self.cleaner = TextCleaner()
    
    def _compile_patterns(self):
        self.compiled_patterns = [(re.compile(p, re.I | re.M), name) for p, name in self.patterns]
    
    def match(self, ocr_results: List[Dict]) -> List[ResumeSection]:
        """将 OCR 结果按标题-内容结构组织"""
        if not ocr_results:
            logger.warning("OCR 结果为空，无法匹配章节")
            return []
        
        sorted_results = sorted(ocr_results, key=lambda r: r["bbox"][1])
        text_lines = self._extract_lines(sorted_results)
        sections = self._match_sections(text_lines)
        
        logger.info(f"标题-内容配对完成，共识别 {len(sections)} 个章节")
        return sections
    
    def _extract_lines(self, ocr_results: List[Dict]) -> List[Dict]:
        lines = []
        for item in ocr_results:
            text = item["text"].strip()
            if not text:
                continue
            is_title = self._detect_title(text)
            lines.append({"text": text, "bbox": item["bbox"], "is_title": is_title, "confidence": item.get("confidence", 1.0)})
        return lines
    
    def _detect_title(self, text: str) -> bool:
        text = text.strip()
        if not text or len(text) > 100:
            return False
        for pattern, _ in self.compiled_patterns:
            if pattern.search(text):
                return True
        if len(text) < 30:
            title_keywords = ["工程师", "经理", "总监", "专家", "主管", "负责人", "Consultant", "Manager", "Director", "Engineer", "Specialist", "Developer", "Designer", "Analyst"]
            if any(kw in text for kw in title_keywords):
                return True
            if re.match(r"^(\d{4}[-/年]\d{0,2}\s*[-~至]\s*)?\d{4}[-/年]\d{0,2}$", text):
                return True
        return False
    
    def _match_sections(self, lines: List[Dict]) -> List[ResumeSection]:
        sections = []
        current_title: Optional[str] = None
        current_content: List[str] = []
        current_bbox: List[float] = []
        current_confidence: float = 1.0
        
        for i, line in enumerate(lines):
            text = line["text"]
            bbox = line["bbox"]
            is_title = line["is_title"]
            confidence = line["confidence"]
            
            if is_title:
                if current_content:
                    sections.append(ResumeSection(title=current_title or "未分类", content="\n".join(current_content).strip(), confidence=current_confidence, bbox=current_bbox, metadata={"source": "ocr"}))
                matched_title = self._get_standard_title(text)
                current_title = matched_title
                current_content = []
                current_bbox = list(bbox)
                current_confidence = confidence
            else:
                if self._is_continuation(line, lines, i):
                    current_content.append(text)
                    current_bbox = self._merge_bbox(current_bbox, bbox)
                else:
                    current_content.append(text)
                    current_bbox = self._merge_bbox(current_bbox, bbox)
        
        if current_content:
            sections.append(ResumeSection(title=current_title or "未分类", content="\n".join(current_content).strip(), confidence=current_confidence, bbox=current_bbox))
        
        sections = self._post_process(sections)
        return sections
    
    def _get_standard_title(self, text: str) -> str:
        for pattern, name in self.compiled_patterns:
            if pattern.search(text):
                return name
        return text
    
    def _is_continuation(self, line: Dict, all_lines: List[Dict], index: int) -> bool:
        bbox = line["bbox"]
        text = line["text"]
        
        if index + 1 < len(all_lines):
            next_line = all_lines[index + 1]
            next_bbox = next_line["bbox"]
            y_diff = abs(bbox[1] - next_bbox[1])
            if y_diff < 10:
                return True
        
        if text.startswith(("•", "-", "·", "※", "◆", "★", "●", "○", "·", "∗")):
            return True
        if re.match(r'^\d+[.、)）]', text):
            return True
        return False
    
    def _merge_bbox(self, bbox1: List[float], bbox2: List[float]) -> List[float]:
        if not bbox1:
            return bbox2
        if not bbox2:
            return bbox1
        return [min(bbox1[0], bbox2[0]), min(bbox1[1], bbox2[1]), max(bbox1[2], bbox2[2]), max(bbox1[3], bbox2[3])]
    
    def _post_process(self, sections: List[ResumeSection]) -> List[ResumeSection]:
        sections = [s for s in sections if s.content.strip()]
        merged = []
        for section in sections:
            if merged and merged[-1].title == section.title:
                merged[-1].content += "\n" + section.content
                merged[-1].bbox = self._merge_bbox(merged[-1].bbox, section.bbox)
                merged[-1].confidence = (merged[-1].confidence + section.confidence) / 2
            else:
                merged.append(section)
        deduplicated = self._deduplicate_sections(merged)
        return deduplicated
    
    def _deduplicate_sections(self, sections: List[ResumeSection]) -> List[ResumeSection]:
        if not sections:
            return []
        deduplicated = [sections[0]]
        for section in sections[1:]:
            last = deduplicated[-1]
            if section.title == last.title and self._calculate_similarity(section.content, last.content) > 0.8:
                continue
            deduplicated.append(section)
        return deduplicated
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        set1 = set(text1)
        set2 = set(text2)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def add_pattern(self, pattern: str, title: str):
        compiled = re.compile(pattern, re.I | re.M)
        self.compiled_patterns.append((compiled, title))
        logger.info(f"添加标题模式: {pattern} -> {title}")
