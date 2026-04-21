"""
数据模型单元测试
"""

import pytest
from datetime import datetime
from models.resume import Resume, ResumeSection


class TestResumeSection:
    """ResumeSection 测试"""
    
    def test_create_section(self):
        """测试创建章节"""
        section = ResumeSection(
            title="姓名",
            content="张三",
            confidence=0.95
        )
        assert section.title == "姓名"
        assert section.content == "张三"
        assert section.confidence == 0.95
    
    def test_default_confidence(self):
        """测试默认置信度"""
        section = ResumeSection(title="测试", content="内容")
        assert section.confidence == 1.0
    
    def test_empty_bbox(self):
        """测试默认边界框"""
        section = ResumeSection(title="测试", content="内容")
        assert section.bbox == []
    
    def test_metadata(self):
        """测试元数据"""
        section = ResumeSection(
            title="教育背景",
            content="某大学",
            metadata={"school": "某大学", "major": "计算机"}
        )
        assert section.metadata["school"] == "某大学"


class TestResume:
    """Resume 测试"""
    
    @pytest.fixture
    def sample_resume(self):
        """创建示例简历"""
        return Resume(
            file_name="test.pdf",
            file_type="pdf",
            sections=[
                ResumeSection(title="姓名", content="李四", confidence=0.95),
                ResumeSection(title="教育背景", content="某大学", confidence=0.90),
                ResumeSection(title="工作经历", content="某公司", confidence=0.85),
            ],
            raw_text="姓名: 李四\n教育背景: 某大学"
        )
    
    def test_create_resume(self, sample_resume):
        """测试创建简历"""
        assert sample_resume.file_name == "test.pdf"
        assert sample_resume.file_type == "pdf"
        assert len(sample_resume.sections) == 3
    
    def test_get_section(self, sample_resume):
        """测试按标题查找章节"""
        section = sample_resume.get_section("姓名")
        assert section is not None
        assert section.content == "李四"
    
    def test_get_section_fuzzy_match(self, sample_resume):
        """测试模糊匹配"""
        section = sample_resume.get_section("教育")
        assert section is not None
        assert "大学" in section.content
    
    def test_get_section_not_found(self, sample_resume):
        """测试查找不存在的章节"""
        section = sample_resume.get_section("不存在的章节")
        assert section is None
    
    def test_get_all_titles(self, sample_resume):
        """测试获取所有标题"""
        titles = sample_resume.get_all_titles()
        assert len(titles) == 3
        assert "姓名" in titles
        assert "教育背景" in titles
    
    def test_to_dict(self, sample_resume):
        """测试转换为字典"""
        data = sample_resume.to_dict()
        assert "sections" in data
        assert "raw_text" in data
        assert "file_name" in data
        assert len(data["sections"]) == 3
    
    def test_to_rag_format(self, sample_resume):
        """测试 RAG 格式转换"""
        rag_data = sample_resume.to_rag_format()
        assert len(rag_data) == 3
        assert "id" in rag_data[0]
        assert "content" in rag_data[0]
        assert "metadata" in rag_data[0]
        assert rag_data[0]["content"].startswith("【")
    
    def test_to_text_format(self, sample_resume):
        """测试纯文本格式"""
        text = sample_resume.to_text_format()
        assert "简历文件: test.pdf" in text
        assert "【姓名】" in text
        assert "李四" in text
    
    def test_empty_resume(self):
        """测试空简历"""
        resume = Resume(file_name="empty.pdf", file_type="pdf")
        assert len(resume.sections) == 0
        assert resume.get_section("任意") is None
        assert resume.get_all_titles() == []
