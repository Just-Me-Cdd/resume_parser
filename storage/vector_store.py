"""
向量存储接口（预留 RAG 支持）
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from models.resume import Resume, ResumeSection
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VectorEntry:
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VectorStoreInterface(ABC):
    """向量存储抽象接口"""
    
    @abstractmethod
    def add(self, entries: List[VectorEntry]) -> bool:
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5, filter_criteria: Optional[Dict] = None) -> List[Dict]:
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        pass
    
    @abstractmethod
    def delete_by_filter(self, filter_criteria: Dict) -> bool:
        pass
    
    @abstractmethod
    def count(self) -> int:
        pass
    
    @abstractmethod
    def exists(self) -> bool:
        pass


class ChromaVectorStore(VectorStoreInterface):
    """ChromaDB 向量存储实现（示例）"""
    
    def __init__(self, collection_name: str = "resume_sections", persist_directory: str = "./chroma_db", embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self._client = None
        self._collection = None
        self._embedding_function = None
    
    def _initialize(self):
        if self._client is not None:
            return
        
        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
            
            logger.info("初始化 ChromaDB...")
            self._client = chromadb.PersistentClient(path=self.persist_directory, settings=Settings(anonymized_telemetry=False))
            logger.info(f"加载 Embedding 模型: {self.embedding_model}")
            self._embedding_function = SentenceTransformer(self.embedding_model)
            self._collection = self._client.get_or_create_collection(name=self.collection_name, metadata={"description": "Resume sections vector store"})
            logger.info(f"ChromaDB 初始化完成，集合: {self.collection_name}")
            
        except ImportError as e:
            logger.error("ChromaDB 未安装，请运行: pip install chromadb sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise
    
    def add(self, entries: List[VectorEntry]) -> bool:
        self._initialize()
        try:
            contents = [e.content for e in entries]
            embeddings = self._embedding_function.encode(contents).tolist()
            ids = [e.id for e in entries]
            metadatas = [e.metadata for e in entries]
            self._collection.add(ids=ids, embeddings=embeddings, documents=contents, metadatas=metadatas)
            logger.info(f"添加 {len(entries)} 个向量条目")
            return True
        except Exception as e:
            logger.error(f"添加向量条目失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, filter_criteria: Optional[Dict] = None) -> List[Dict]:
        self._initialize()
        try:
            query_embedding = self._embedding_function.encode([query]).tolist()
            results = self._collection.query(query_embeddings=query_embedding, n_results=top_k, where=filter_criteria)
            formatted = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    idx = results["ids"][0].index(doc_id)
                    formatted.append({"id": doc_id, "content": results["documents"][0][idx], "score": 1 - results["distances"][0][idx], "metadata": results["metadatas"][0][idx]})
            return formatted
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    def delete(self, ids: List[str]) -> bool:
        self._initialize()
        try:
            self._collection.delete(ids=ids)
            logger.info(f"删除 {len(ids)} 个向量条目")
            return True
        except Exception as e:
            logger.error(f"删除向量条目失败: {e}")
            return False
    
    def delete_by_filter(self, filter_criteria: Dict) -> bool:
        self._initialize()
        try:
            self._collection.delete(where=filter_criteria)
            logger.info(f"按条件删除向量条目: {filter_criteria}")
            return True
        except Exception as e:
            logger.error(f"删除向量条目失败: {e}")
            return False
    
    def count(self) -> int:
        self._initialize()
        return self._collection.count()
    
    def exists(self) -> bool:
        return self._client is not None


class SimpleInMemoryVectorStore(VectorStoreInterface):
    """简单的内存向量存储（用于测试或小规模数据）"""
    
    def __init__(self):
        self._entries: Dict[str, VectorEntry] = {}
        self._embeddings: Dict[str, List[float]] = {}
    
    def add(self, entries: List[VectorEntry]) -> bool:
        try:
            for entry in entries:
                self._entries[entry.id] = entry
                if entry.embedding is None:
                    self._embeddings[entry.id] = self._simple_hash(entry.content)
                else:
                    self._embeddings[entry.id] = entry.embedding
            logger.info(f"添加 {len(entries)} 个向量条目（内存存储）")
            return True
        except Exception as e:
            logger.error(f"添加向量条目失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, filter_criteria: Optional[Dict] = None) -> List[Dict]:
        if not self._entries:
            return []
        query_keywords = query.lower().split()
        scored = []
        for entry_id, entry in self._entries.items():
            content_lower = entry.content.lower()
            score = sum(1 for kw in query_keywords if kw in content_lower)
            if score > 0:
                if filter_criteria:
                    if not self._match_filter(entry.metadata, filter_criteria):
                        continue
                scored.append({"id": entry_id, "content": entry.content, "score": score / len(query_keywords), "metadata": entry.metadata})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
    
    def _match_filter(self, metadata: Dict, filter_criteria: Dict) -> bool:
        for key, value in filter_criteria.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def _simple_hash(self, text: str, dim: int = 128) -> List[float]:
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        vector = []
        for i in range(dim):
            byte_idx = i % len(hash_bytes)
            value = hash_bytes[byte_idx] / 255.0
            vector.append(value)
        return vector
    
    def delete(self, ids: List[str]) -> bool:
        for entry_id in ids:
            self._entries.pop(entry_id, None)
            self._embeddings.pop(entry_id, None)
        logger.info(f"删除 {len(ids)} 个向量条目")
        return True
    
    def delete_by_filter(self, filter_criteria: Dict) -> bool:
        to_delete = []
        for entry_id, entry in self._entries.items():
            if self._match_filter(entry.metadata, filter_criteria):
                to_delete.append(entry_id)
        return self.delete(to_delete)
    
    def count(self) -> int:
        return len(self._entries)
    
    def exists(self) -> bool:
        return True


def get_vector_store(store_type: str = "simple", **kwargs) -> VectorStoreInterface:
    """获取向量存储实例"""
    stores = {"simple": SimpleInMemoryVectorStore, "chroma": ChromaVectorStore}
    store_class = stores.get(store_type.lower())
    if store_class is None:
        raise ValueError(f"不支持的存储类型: {store_type}")
    return store_class(**kwargs)
