"""
简历解析工具 - 存储模块（RAG 预留接口）
"""

from storage.vector_store import VectorStoreInterface, ChromaVectorStore
from storage.rag_retriever import RAGRetriever

__all__ = ["VectorStoreInterface", "ChromaVectorStore", "RAGRetriever"]
