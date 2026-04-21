"""
存储模块单元测试
"""

import pytest
from storage.vector_store import (
    VectorEntry,
    VectorStoreInterface,
    SimpleInMemoryVectorStore,
    get_vector_store
)
from models.resume import Resume, ResumeSection


class TestVectorEntry:
    """VectorEntry 测试"""
    
    def test_create_entry(self):
        """测试创建向量条目"""
        entry = VectorEntry(
            id="test_1",
            content="这是一段测试内容",
            metadata={"source": "test"}
        )
        assert entry.id == "test_1"
        assert entry.content == "这是一段测试内容"
        assert entry.metadata["source"] == "test"
    
    def test_default_metadata(self):
        """测试默认元数据"""
        entry = VectorEntry(id="test_1", content="内容")
        assert entry.metadata == {}


class TestSimpleInMemoryVectorStore:
    """内存向量存储测试"""
    
    @pytest.fixture
    def store(self):
        """创建测试存储"""
        return SimpleInMemoryVectorStore()
    
    @pytest.fixture
    def sample_entries(self):
        """创建示例数据"""
        return [
            VectorEntry(
                id="doc_1",
                content="张三，Python开发工程师，5年经验",
                metadata={"type": "work", "name": "张三"}
            ),
            VectorEntry(
                id="doc_2",
                content="李四，产品经理，3年经验",
                metadata={"type": "work", "name": "李四"}
            ),
            VectorEntry(
                id="doc_3",
                content="王五，数据分析师，2年经验",
                metadata={"type": "work", "name": "王五"}
            ),
        ]
    
    def test_add_entries(self, store, sample_entries):
        """测试添加条目"""
        result = store.add(sample_entries)
        assert result == True
        assert store.count() == 3
    
    def test_search_basic(self, store, sample_entries):
        """测试基础搜索"""
        store.add(sample_entries)
        
        results = store.search("Python开发")
        assert len(results) > 0
        assert results[0]["id"] == "doc_1"
    
    def test_search_with_top_k(self, store, sample_entries):
        """测试限制结果数量"""
        store.add(sample_entries)
        
        results = store.search("经验", top_k=1)
        assert len(results) <= 1
    
    def test_search_with_filter(self, store, sample_entries):
        """测试带过滤的搜索"""
        store.add(sample_entries)
        
        results = store.search("经验", filter_criteria={"type": "work"})
        assert all(r["metadata"]["type"] == "work" for r in results)
    
    def test_delete_entries(self, store, sample_entries):
        """测试删除条目"""
        store.add(sample_entries)
        assert store.count() == 3
        
        store.delete(["doc_1"])
        assert store.count() == 2
    
    def test_delete_by_filter(self, store, sample_entries):
        """测试按条件删除"""
        store.add(sample_entries)
        assert store.count() == 3
        
        store.delete_by_filter({"name": "张三"})
        assert store.count() == 2
    
    def test_count(self, store, sample_entries):
        """测试计数"""
        assert store.count() == 0
        store.add(sample_entries[:2])
        assert store.count() == 2
        store.add(sample_entries[2:])
        assert store.count() == 3
    
    def test_exists(self, store, sample_entries):
        """测试存在性检查"""
        assert store.exists() == False
        store.add(sample_entries)
        assert store.exists() == True
    
    def test_empty_search(self, store):
        """测试空存储搜索"""
        results = store.search("任何内容")
        assert len(results) == 0
    
    def test_no_match_search(self, store, sample_entries):
        """测试无匹配搜索"""
        store.add(sample_entries)
        results = store.search("完全不匹配的内容 xyz123")
        assert len(results) == 0


class TestGetVectorStore:
    """向量存储工厂测试"""
    
    def test_get_simple_store(self):
        """测试获取简单存储"""
        store = get_vector_store("simple")
        assert isinstance(store, SimpleInMemoryVectorStore)
    
    def test_unknown_store_type(self):
        """测试未知存储类型"""
        with pytest.raises(ValueError):
            get_vector_store("unknown_type")


class TestIntegration:
    """集成测试"""
    
    def test_resume_to_vector_store(self):
        """测试简历到向量存储的完整流程"""
        # 创建简历
        resume = Resume(
            file_name="test.pdf",
            file_type="pdf",
            sections=[
                ResumeSection(title="姓名", content="张三"),
                ResumeSection(title="工作经历", content="在某公司担任开发"),
            ]
        )
        
        # 转换为 RAG 格式
        rag_entries = resume.to_rag_format()
        entries = [
            VectorEntry(
                id=e["id"],
                content=e["content"],
                metadata=e["metadata"]
            )
            for e in rag_entries
        ]
        
        # 添加到存储
        store = SimpleInMemoryVectorStore()
        store.add(entries)
        
        # 搜索
        results = store.search("张三")
        assert len(results) > 0
        
        results = store.search("工作")
        assert len(results) > 0
