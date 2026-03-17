from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection

connections.connect(host='localhost', port='19530')

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=200),
    # 核心字段：存储建表 DDL 或字段描述字符串
    FieldSchema(name="schema_text", dtype=DataType.VARCHAR, max_length=4096),
    # 向量字段 (nomic-embed-text 768维)
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768)
]

schema = CollectionSchema(fields, "Dofi 数据字典 - 存放表结构与指标口径")
collection = Collection("dofi_data_dictionary", schema)

# 创建 HNSW 索引
index_params = {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
collection.create_index("vector", index_params)
collection.load()
print("✅ 数据字典向量库初始化完成！")