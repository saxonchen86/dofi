import ollama
from pymilvus import Collection, connections

# 假设你的两张表
tables = [
    {
        "name": "user_info",
        "ddl": "Table: user_info (用户信息表); Columns: [user_id (BIGINT, 主键), user_name (STRING), register_ip (STRING), country (STRING, 越南/中国等)]"
    },
    {
        "name": "user_orders",
        "ddl": "Table: user_orders (订单流水表); Columns: [order_id (BIGINT), user_id (BIGINT, 关联user_info), amount (DECIMAL), currency (STRING, USDT/VND), create_time (TIMESTAMP)]"
    }
]

def ingest():
    connections.connect(host='localhost', port='19530')
    col = Collection("dofi_data_dictionary")
    
    for t in tables:
        # 使用 nomic-embed-text 生成向量
        res = ollama.embeddings(model="nomic-embed-text", prompt=t['ddl'])
        vector = res['embedding']
        
        col.insert([
            [t['name']],
            [t['ddl']],
            [vector]
        ])
    col.flush()
    print(f"🚀 已成功存储 {len(tables)} 张表的结构信息")

ingest()