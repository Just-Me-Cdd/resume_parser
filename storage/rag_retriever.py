"""
RAG 检索器 - 完整的语义检索实现
"""

from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading

from models.resume import Resume, ResumeSection
from storage.vector_store import VectorStoreInterface, VectorEntry, get_vector_store
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    section: ResumeSection
    resume_id: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class ResumeIndex:
    """简历索引信息"""
    resume_id: str
    file_name: str
    file_type: str
    section_count: int
    added_at: datetime
    last_accessed: datetime = field(default_factory=datetime.now)


class RAGRetriever:
    """
    RAG 检索器 - 完整的语义检索实现
    
    功能特性:
    - 向量化语义检索
    - 支持按简历ID过滤
    - 支持按章节标题检索
    - 线程安全的索引管理
    - 检索结果排序与评分
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStoreInterface] = None,
        store_type: str = "simple",
        **vector_store_kwargs
    ):
        """
        初始化 RAG 检索器
        
        Args:
            vector_store: 自定义向量存储实例
            store_type: 向量存储类型 (simple/chroma)
            **vector_store_kwargs: 传递给向量存储的参数
        """
        if vector_store is None:
            self.vector_store = get_vector_store(store_type, **vector_store_kwargs)
        else:
            self.vector_store = vector_store
        
        self._initialized = False
        self._lock = threading.Lock()
        
        # 索引管理
        self._resume_index: Dict[str, ResumeIndex] = {}
        self._section_index: Dict[str, str] = {}  # section_id -> resume_id
    
    def initialize(self):
        """初始化检索器"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            if hasattr(self.vector_store, '_initialize'):
                self.vector_store._initialize()
            
            self._initialized = True
            logger.info("RAG 检索器初始化完成")
    
    def add_resume(self, resume: Resume) -> bool:
        """
        添加简历到知识库
        
        Args:
            resume: 简历对象
            
        Returns:
            bool: 添加是否成功
        """
        self.initialize()
        
        try:
            # 转换为 RAG 格式
            rag_entries = resume.to_rag_format()
            
            # 创建向量条目
            entries = [
                VectorEntry(
                    id=entry["id"],
                    content=entry["content"],
                    metadata=entry["metadata"]
                )
                for entry in rag_entries
            ]
            
            # 添加到向量存储
            success = self.vector_store.add(entries)
            
            if success:
                # 更新索引
                with self._lock:
                    resume_id = resume.file_name
                    self._resume_index[resume_id] = ResumeIndex(
                        resume_id=resume_id,
                        file_name=resume.file_name,
                        file_type=resume.file_type,
                        section_count=len(resume.sections),
                        added_at=datetime.now()
                    )
                    
                    for entry in rag_entries:
                        self._section_index[entry["id"]] = resume_id
                
                logger.info(f"简历已添加: {resume.file_name}，共 {len(entries)} 个章节")
            
            return success
            
        except Exception as e:
            logger.error(f"添加简历失败: {e}")
            return False
    
    def add_section(
        self,
        section: ResumeSection,
        resume_id: str,
        section_index: int
    ) -> bool:
        """
        添加单个章节到知识库
        
        Args:
            section: 简历章节
            resume_id: 简历ID
            section_index: 章节索引
            
        Returns:
            bool: 添加是否成功
        """
        self.initialize()
        
        entry = VectorEntry(
            id=f"{resume_id}_{section_index}",
            content=f"【{section.title}】{section.content}",
            metadata={
                "title": section.title,
                "content": section.content,
                "resume_file": resume_id,
                "section_index": section_index
            }
        )
        
        success = self.vector_store.add([entry])
        
        if success:
            with self._lock:
                self._section_index[entry.id] = resume_id
        
        return success
    
    def retrieve(
        self,
        query: str,
        resume_id: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[RetrievalResult]:
        """
        语义检索
        
        Args:
            query: 检索查询
            resume_id: 可选，限定检索特定简历
            top_k: 返回结果数量
            min_score: 最低分数阈值
            
        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        self.initialize()
        
        filter_criteria = None
        if resume_id:
            filter_criteria = {"resume_file": resume_id}
        
        # 执行搜索
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            filter_criteria=filter_criteria
        )
        
        # 转换结果
        retrieval_results = []
        with self._lock:
            for result in results:
                if result["score"] < min_score:
                    continue
                
                metadata = result.get("metadata", {})
                section = ResumeSection(
                    title=metadata.get("title", ""),
                    content=metadata.get("content", ""),
                    metadata=metadata
                )
                
                result_resume_id = metadata.get("resume_file", "")
                
                # 更新访问时间
                if result_resume_id in self._resume_index:
                    self._resume_index[result_resume_id].last_accessed = datetime.now()
                
                retrieval_results.append(RetrievalResult(
                    section=section,
                    resume_id=result_resume_id,
                    score=result["score"],
                    metadata=metadata
                ))
        
        logger.info(f"检索完成: query='{query}', 结果数={len(retrieval_results)}")
        return retrieval_results
    
    def retrieve_by_title(
        self,
        title: str,
        resume_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        按章节标题检索
        
        Args:
            title: 章节标题
            resume_id: 可选，限定检索特定简历
            top_k: 返回结果数量
            
        Returns:
            List[RetrievalResult]: 检索结果
        """
        query = f"【{title}】"
        return self.retrieve(query, resume_id, top_k)
    
    def retrieve_skills(
        self,
        resume_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """检索技能相关章节"""
        return self.retrieve_by_title("技能", resume_id, top_k)
    
    def retrieve_education(
        self,
        resume_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """检索教育背景"""
        return self.retrieve_by_title("教育", resume_id, top_k)
    
    def retrieve_experience(
        self,
        resume_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """检索工作经历"""
        return self.retrieve_by_title("工作", resume_id, top_k)
    
    def delete_resume(self, resume_id: str) -> bool:
        """
        删除简历及其所有章节
        
        Args:
            resume_id: 简历ID
            
        Returns:
            bool: 删除是否成功
        """
        self.initialize()
        
        success = self.vector_store.delete_by_filter({"resume_file": resume_id})
        
        if success:
            with self._lock:
                # 清理索引
                if resume_id in self._resume_index:
                    del self._resume_index[resume_id]
                
                # 清理章节索引
                section_ids_to_remove = [
                    sid for sid, rid in self._section_index.items()
                    if rid == resume_id
                ]
                for sid in section_ids_to_remove:
                    del self._section_index[sid]
                
                logger.info(f"删除简历: {resume_id}")
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        self.initialize()
        
        total_count = self.vector_store.count()
        
        return {
            "total_sections": total_count,
            "total_resumes": len(self._resume_index),
            "store_type": self.vector_store.__class__.__name__,
            "initialized": self._initialized,
            "resumes": [
                {
                    "resume_id": idx.resume_id,
                    "file_type": idx.file_type,
                    "section_count": idx.section_count,
                    "added_at": idx.added_at.isoformat()
                }
                for idx in self._resume_index.values()
            ]
        }
    
    def get_resume_info(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """获取简历详情"""
        with self._lock:
            if resume_id not in self._resume_index:
                return None
            
            idx = self._resume_index[resume_id]
            return {
                "resume_id": idx.resume_id,
                "file_name": idx.file_name,
                "file_type": idx.file_type,
                "section_count": idx.section_count,
                "added_at": idx.added_at.isoformat(),
                "last_accessed": idx.last_accessed.isoformat()
            }
    
    def clear(self) -> bool:
        """
        清空知识库
        
        Returns:
            bool: 清空是否成功
        """
        logger.warning("清空知识库...")
        
        try:
            with self._lock:
                self.vector_store.delete_by_filter({})
                self._resume_index.clear()
                self._section_index.clear()
                
                logger.info("知识库已清空")
                return True
                
        except Exception as e:
            logger.error(f"清空知识库失败: {e}")
            return False


class ResumeQueryEngine:
    """
    简历查询引擎 - 基于规则的查询
    
    提供快速的关键字匹配查询，适用于简单场景
    """
    
    def __init__(self, resumes: Optional[List[Resume]] = None):
        self.resumes: List[Resume] = resumes or []
        self._title_index: Dict[str, List[tuple]] = {}  # title -> [(resume_id, section)]
        self._content_index: Dict[str, List[tuple]] = {}  # keyword -> [(resume_id, section)]
        self._build_index()
    
    def add_resume(self, resume: Resume):
        """添加简历并重建索引"""
        self.resumes.append(resume)
        self._build_index()
    
    def remove_resume(self, resume_id: str):
        """移除简历"""
        self.resumes = [r for r in self.resumes if r.file_name != resume_id]
        self._build_index()
    
    def _build_index(self):
        """构建倒排索引"""
        self._title_index.clear()
        self._content_index.clear()
        
        for resume in self.resumes:
            resume_id = resume.file_name
            
            for section in resume.sections:
                # 标题索引
                title_key = section.title.lower()
                if title_key not in self._title_index:
                    self._title_index[title_key] = []
                self._title_index[title_key].append((resume_id, section))
                
                # 内容关键词索引
                for keyword in self._extract_keywords(section.content):
                    if keyword not in self._content_index:
                        self._content_index[keyword] = []
                    self._content_index[keyword].append((resume_id, section))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        # 简单的中文/英文词分割
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
        # 过滤短词
        return [w for w in words if len(w) >= 2]
    
    def query(self, query: str) -> List[Dict]:
        """
        查询简历
        
        Args:
            query: 查询字符串
            
        Returns:
            匹配的章节列表
        """
        query_lower = query.lower()
        results = []
        seen = set()
        
        # 标题匹配
        for title, sections in self._title_index.items():
            if query_lower in title:
                for resume_id, section in sections:
                    key = (resume_id, section.title)
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "title": section.title,
                            "content": section.content,
                            "resume_id": resume_id,
                            "matched_on": "title",
                            "confidence": 1.0
                        })
        
        # 内容匹配
        keywords = self._extract_keywords(query)
        for keyword in keywords:
            if keyword in self._content_index:
                for resume_id, section in self._content_index[keyword]:
                    key = (resume_id, section.title)
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "title": section.title,
                            "content": section.content,
                            "resume_id": resume_id,
                            "matched_on": "content",
                            "confidence": 0.8
                        })
        
        return results
    
    def get_all_education(self, resume_id: Optional[str] = None) -> List[str]:
        """获取所有教育背景"""
        return self._get_sections_by_title("教育", resume_id)
    
    def get_all_work_experience(self, resume_id: Optional[str] = None) -> List[str]:
        """获取所有工作经历"""
        return self._get_sections_by_title("工作", resume_id)
    
    def get_all_skills(self, resume_id: Optional[str] = None) -> List[str]:
        """获取所有技能"""
        return self._get_sections_by_title("技能", resume_id)
    
    def _get_sections_by_title(
        self,
        title_keyword: str,
        resume_id: Optional[str] = None
    ) -> List[str]:
        """按标题获取章节内容"""
        results = []
        keyword_lower = title_keyword.lower()
        
        for title, sections in self._title_index.items():
            if keyword_lower in title:
                for rid, section in sections:
                    if resume_id and rid != resume_id:
                        continue
                    results.append(section.content)
        
        return results
