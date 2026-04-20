"""
PDF 简历解析器
"""

from pathlib import Path
from typing import Union, Optional, List, Dict
import fitz

from parser.base import BaseParser
from parser.image_parser import ImageParser
from extractor.section_matcher import SectionMatcher
from extractor.cleaner import TextCleaner
from models.resume import Resume
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFParser(BaseParser):
    """PDF 简历解析器"""
    SUPPORTED_EXTENSIONS = [".pdf"]
    
    def __init__(self, mode: str = "text", lang: str = "ch", use_gpu: bool = False, image_dpi: int = 300):
        self.mode = mode
        self.image_dpi = image_dpi
        self.image_parser = None
        if mode == "ocr":
            self.image_parser = ImageParser(lang=lang, use_gpu=use_gpu)
        self.matcher = SectionMatcher()
        self.cleaner = TextCleaner()
    
    def parse(self, file_path: Union[str, Path]) -> Resume:
        path = self.validate_file(file_path)
        logger.info(f"开始解析 PDF 简历: {path.name}, 模式: {self.mode}")
        
        if self.mode == "text":
            return self._parse_as_text(path)
        elif self.mode == "ocr":
            return self._parse_as_images(path)
        else:
            raise ValueError(f"不支持的解析模式: {self.mode}")
    
    def _parse_as_text(self, file_path: Path) -> Resume:
        doc = fitz.open(str(file_path))
        all_blocks = []
        
        for page_num, page in enumerate(doc):
            logger.info(f"处理第 {page_num + 1}/{len(doc)} 页...")
            text = page.get_text("text")
            blocks = page.get_text("blocks")
            
            for block in blocks:
                if len(block) >= 5:
                    x0, y0, x1, y1 = block[:4]
                    block_text = block[4].strip()
                    if block_text:
                        all_blocks.append({"text": self.cleaner.clean(block_text), "bbox": [float(x0), float(y0), float(x1), float(y1)], "page": page_num})
        
        doc.close()
        all_blocks.sort(key=lambda b: (b["page"], b["bbox"][1]))
        merged_blocks = self._merge_blocks(all_blocks)
        sections = self.matcher.match(merged_blocks)
        raw_text = "\n".join([b["text"] for b in all_blocks])
        
        resume = Resume(sections=sections, raw_text=raw_text, file_name=file_path.name, file_type="pdf")
        logger.info(f"解析完成，共 {len(doc)} 页，{len(sections)} 个章节")
        return resume
    
    def _parse_as_images(self, file_path: Path) -> Resume:
        if self.image_parser is None:
            raise RuntimeError("OCR 模式未正确初始化")
        
        doc = fitz.open(str(file_path))
        all_ocr_results = []
        
        for page_num, page in enumerate(doc):
            logger.info(f"处理第 {page_num + 1}/{len(doc)} 页...")
            mat = fitz.Matrix(self.image_dpi / 72, self.image_dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            import numpy as np
            from PIL import Image
            import io
            
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img_array = np.array(img)
            
            ocr_results = self.image_parser._ocr_recognize(img_array)
            for result in ocr_results:
                result["page"] = page_num
                all_ocr_results.append(result)
        
        doc.close()
        sections = self.image_parser._match_sections(all_ocr_results)
        raw_text = "\n".join([r["text"] for r in all_ocr_results])
        
        resume = Resume(sections=sections, raw_text=raw_text, file_name=file_path.name, file_type="pdf")
        logger.info(f"解析完成，共 {len(doc)} 页，{len(sections)} 个章节")
        return resume
    
    def _merge_blocks(self, blocks: List[Dict], x_threshold: float = 50, y_threshold: float = 10) -> List[Dict]:
        if not blocks:
            return []
        
        merged = []
        current_group = [blocks[0]]
        
        for block in blocks[1:]:
            prev_block = current_group[-1]
            same_column = abs(block["bbox"][0] - prev_block["bbox"][0]) < x_threshold
            same_page = block.get("page", 0) == prev_block.get("page", 0)
            adjacent = abs(block["bbox"][1] - prev_block["bbox"][3]) < y_threshold
            
            if same_page and same_column and adjacent:
                current_group.append(block)
            else:
                merged.append(self._merge_group(current_group))
                current_group = [block]
        
        if current_group:
            merged.append(self._merge_group(current_group))
        
        return merged
    
    def _merge_group(self, blocks: List[Dict]) -> Dict:
        texts = [b["text"] for b in blocks]
        merged_text = "\n".join(texts)
        min_x = min(b["bbox"][0] for b in blocks)
        min_y = min(b["bbox"][1] for b in blocks)
        max_x = max(b["bbox"][2] for b in blocks)
        max_y = max(b["bbox"][3] for b in blocks)
        return {"text": merged_text, "bbox": [min_x, min_y, max_x, max_y], "page": blocks[0].get("page", 0)}
    
    @classmethod
    def can_parse(cls, file_path: Union[str, Path]) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS
