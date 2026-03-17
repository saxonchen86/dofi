import time
from pymilvus import MilvusClient, DataType
import ollama

class DofiMemory:
    """
    dofi 的向量记忆插件
    架构设计：采用 HNSW 索引以适配 M4 Pro 的多核并行检索性能
    """
    def __init__(self, uri="http://milvus:19530", token=""):
        # 1. 连接 Milvus (确保 dofi 容器和 milvus 在同一 Docker 网络)
        self.client = MilvusClient(uri=uri, token=token)
        self.collection_name = "dofi_knowledge_base"
        self.dim = 768  # nomic-embed-text 模型生成的向量维度
        self._init_collection()

    def _init_collection(self):
        """初始化集合，如果不存在则创建"""
        if not self.client.has_collection(self.collection_name):
            # 定义 Schema：ID + 向量 + 原始文本内容
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=self.dim,
                auto_id=True,
                enable_dynamic_field=True, # 允许存储额外的元数据
                metric_type="COSINE"       # 余弦相似度，最适合语义匹配
            )
            print(f"🚀 [Memory] 集合 {self.collection_name} 已创建")

    def _get_embedding(self, text: str):
        """调用本地 Ollama 生成向量"""
        try:
            response = ollama.embeddings(model="nomic-embed-text", prompt=text)
            return response["embedding"]
        except Exception as e:
            print(f"❌ [Ollama] 向量化失败: {e}")
            return None

    def save(self, text: str, metadata: dict = None):
        """存入记忆：将文本存入 Milvus"""
        vector = self._get_embedding(text)
        if vector:
            data = {"vector": vector, "content": text}
            if metadata:
                data.update(metadata)
            
            res = self.client.insert(collection_name=self.collection_name, data=[data])
            print(f"✅ [Memory] 记忆已存入, ID: {res['ids']}")
            return res
        return None

    def recall(self, query: str, limit: int = 3):
        """回忆：根据关键词检索最相关的片段"""
        query_vector = self._get_embedding(query)
        if not query_vector:
            return []

        # 执行向量搜索
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=limit,
            output_fields=["content"], # 返回原始文本
            search_params={"metric_type": "COSINE", "params": {"ef": 64}} # HNSW 检索参数
        )
        
        # 提取结果
        memory_fragments = [hit['entity']['content'] for hit in results[0]]
        return memory_fragments

# --- 快速测试 ---
if __name__ == "__main__":
    memory = DofiMemory(uri="http://localhost:19530") # 宿主机测试用 localhost
    
    # 存入一条技术笔记
    memory.save(
        "Flink 1.18 引入了新的动态并发控制，能根据负载自动调整 TaskManager 槽位。",
        {"tag": "big-data", "source": "flink-docs"}
    )
    
    # 模拟检索
    time.sleep(1) # 等待索引落盘
    print("🤖 dofi 正在回忆中...")
    fragments = memory.recall("Flink 的自动扩展功能如何？")
    for i, f in enumerate(fragments):
        print(f"片段 {i+1}: {f}")