"""
RAG 检索器（预留接口）
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from models.resume import Resume, ResumeSection
from storage.vector_store import VectorStoreInterface, VectorEntry, get_vector_store
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    section: ResumeSection
    resume_id: str
    score: float
    metadata: Dict[str, Any]


class RAGRetriever:
    """RAG 检索器（预留接口）"""
    
    def __init__(self, vector_store: Optional[VectorStoreInterface] = None, store_type: str = "simple", **vector_store_kwargs):
        if vector_store is None:
            self.vector_store = get_vector_store(store_type, **vector_store_kwargs)
        else:
            self.vector_store = vector_store
        self._initialized = False
    
    def initialize(self):
        if self._initialized:
            return
        if hasattr(self.vector_store, '_initialize'):
            self.vector_store._initialize()
        self._initialized = True
        logger.info("RAG 检索器初始化完成")
    
    def add_resume(self, resume: Resume) -> bool:
        self.initialize()
        try:
            rag_entries = resume.to_rag_format()
            entries = [VectorEntry(id=entry["id"], content=entry["content"], metadata=entry["metadata"]) for entry in rag_entries]
            success = self.vector_store.add(entries)
            if success:
                logger.info(f"简历已添加: {resume.file_name}，共 {len(entries)} 个章节")
            return success
        except Exception as e:
            logger.error(f"添加简历失败: {e}")
            return False
    
    def add_section(self, section: ResumeSection, resume_id: str, section_index: int) -> bool:
        self.initialize()
        entry = VectorEntry(id=f"{resume_id}_{section_index}", content=f"【{section.title}】{section.content}", metadata={"title": section.title, "content": section.content, "resume_file": resume_id, "section_index": section_index})
        return self.vector_store.add([entry])
    
    def retrieve(self, query: str, resume_id: Optional[str] = None, top_k: int = 5, min_score: float = 0.0) -> List[RetrievalResult]:
        self.initialize()
        filter_criteria = None
        if resume_id:
            filter_criteria = {"resume_file": resume_id}
        results = self.vector_store.search(query=query, top_k=top_k, filter_criteria=filter_criteria)
        retrieval_results = []
        for result in results:
            if result["score"] < min_score:
                continue
            metadata = result.get("metadata", {})
            section = ResumeSection(title=metadata.get("title", ""), content=metadata.get("content", ""), metadata=metadata)
            retrieval_results.append(RetrievalResult(section=section, resume_id=metadata.get("resume_file", ""), score=result["score"], metadata=metadata))
        logger.info(f"检索完成: query='{query}', 结果数={len(retrieval_results)}")
        return retrieval_results
    
    def retrieve_by_title(self, title: str, resume_id: Optional[str] = None, top_k: int = 5) -> List[RetrievalResult]:
        query = f"【{title}】"
        return self.retrieve(query, resume_id, top_k)
    
    def delete_resume(self, resume_id: str) -> bool:
        self.initialize()
        success = self.vector_store.delete_by_filter({"resume_file": resume_id})
        if success:
            logger.info(f"删除简历: {resume_id}")
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        self.initialize()
        total_count = self.vector_store.count()
        return {"total_sections": total_count, "store_type": self.vector_store.__class__.__name__, "initialized": self._initialized}
    
    def clear(self) -> bool:
        logger.warning("清空知识库...")
        try:
            self.vector_store.delete_by_filter({})
            logger.info("知识库已清空")
            return True
        except Exception as e:
            logger.error(f"清空知识库失败: {e}")
            return False


class ResumeQueryEngine:
    """简历查询引擎（基于规则的查询）"""
    
    def __init__(self, resumes: Optional[List[Resume]] = None):
        self.resumes = resumes or []
        self._index: Dict[str, List[ResumeSection]] = {}
        self._build_index()
    
    def add_resume(self, resume: Resume):
        self.resumes.append(resume)
        self._build_index()
    
    def _build_index(self):
        self._index = {}
        for resume in self.resumes:
            for section in resume.sections:
                title = section.title.lower()
                if title not in self._index:
                    self._index[title] = []
                self._index[title].append(section)
    
    def query(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for title, sections in self._index.items():
            if query_lower in title:
                for section in sections:
                    results.append({"title": section.title, "content": section.content, "matched_on": "title"})
        return results
    
    def get_all_education(self, resume_id: Optional[str] = None) -> List[str]:
        return self._get_sections_by_title("教育", resume_id)
    
    def get_all_work_experience(self, resume_id: Optional[str] = None) -> List[str]:
        return self._get_sections_by_title("工作", resume_id)
    
    def get_all_skills(self, resume_id: Optional[str] = None) -> List[str]:
        return self._get_sections_by_title("技能", resume_id)
    
    def _get_sections_by_title(self, title_keyword: str, resume_id: Optional[str] = None) -> List[str]:
        results = []
        for resume in self.resumes:
            if resume_id and resume.file_name != resume_id:
                continue
            for section in resume.sections:
                if title_keyword in section.title.lower():
                    results.append(section.content)
        return results
