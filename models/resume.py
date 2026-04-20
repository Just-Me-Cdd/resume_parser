"""
简历数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ResumeSection(BaseModel):
    """简历章节（标题-内容配对）"""
    title: str = Field(description="章节标题")
    content: str = Field(description="对应内容")
    confidence: float = Field(default=1.0, description="识别置信度 0-1")
    bbox: List[float] = Field(default_factory=list, description="边界框坐标 [x1,y1,x2,y2]")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元信息")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "姓名",
                "content": "张三",
                "confidence": 0.95,
                "bbox": [100, 50, 200, 80]
            }
        }


class Resume(BaseModel):
    """完整简历结构"""
    sections: List[ResumeSection] = Field(default_factory=list)
    raw_text: str = Field(default="", description="原始文本（保留）")
    file_name: str = Field(default="", description="文件名")
    file_type: str = Field(default="", description="文件类型 pdf/docx/image")
    parsed_at: datetime = Field(default_factory=datetime.now)

    def get_section(self, title: str) -> Optional[ResumeSection]:
        """按标题查找章节（模糊匹配）"""
        title_lower = title.lower()
        for section in self.sections:
            if title_lower in section.title.lower():
                return section
        return None

    def get_all_titles(self) -> List[str]:
        """获取所有章节标题"""
        return [s.title for s in self.sections]

    def to_dict(self) -> dict:
        """转为字典，便于 JSON 存储"""
        return {
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "confidence": s.confidence
                }
                for s in self.sections
            ],
            "raw_text": self.raw_text,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "parsed_at": self.parsed_at.isoformat()
        }

    def to_rag_format(self) -> List[Dict[str, Any]]:
        """转为 RAG 检索格式（便于后续向量化）"""
        return [
            {
                "id": f"{self.file_name}_{i}",
                "content": f"【{s.title}】{s.content}",
                "metadata": {
                    "title": s.title,
                    "content": s.content,
                    "resume_file": self.file_name,
                    "section_index": i
                }
            }
            for i, s in enumerate(self.sections)
        ]

    def to_text_format(self) -> str:
        """转为纯文本格式，便于阅读"""
        lines = []
        lines.append(f"简历文件: {self.file_name}")
        lines.append(f"类型: {self.file_type}")
        lines.append(f"解析时间: {self.parsed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        for section in self.sections:
            lines.append(f"\n【{section.title}】")
            lines.append(section.content)
        
        return "\n".join(lines)
