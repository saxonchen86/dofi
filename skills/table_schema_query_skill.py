"""
表格关联查询技能
用于处理用户关于表格关联查询的问题，从 Milvus 中获取表格 schema 信息并生成正确的 SQL 语句
"""
import ollama
from pymilvus import connections, Collection
import os
import re

def get_table_schema(query: str) -> str:
    """
    根据用户提问，从 Milvus 向量库中检索最相关的表结构、DDL 和字段定义。
    """
    try:
        # 1. 建立连接 (自适应宿主机环境)
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        connections.connect(host=milvus_host, port='19530')

        # 2. 对齐我们之前定义的 Collection
        collection_name = "dofi_data_dictionary"
        collection = Collection(collection_name)

        # 3. 将用户的提问向量化 (对齐 nomic-embed-text)
        # 提示：这里使用 Ollama 宿主机地址
        ollama_host = os.getenv("OLLAMA_HOST", "localhost")
        client = ollama.Client(host=f'http://{ollama_host}:11434')

        embedding_res = client.embeddings(
            model="nomic-embed-text",
            prompt=query
        )
        query_vector = embedding_res['embedding']

        # 4. 执行向量检索 (检索最相关的 3 张表)
        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=3,
            output_fields=["table_name", "schema_text"]
        )

        # 5. 格式化结果供 Dofi 阅读
        if not results[0]:
            return "⚠️ 未在数据字典中找到匹配的表结构，请检查是否已录入 DDL。"

        schemas = []
        for hit in results[0]:
            table_info = (
                f"--- Table: {hit.entity.get('table_name')} ---\n"
                f"DDL/Schema: {hit.entity.get('schema_text')}\n"
            )
            schemas.append(table_info)

        return "\n".join(schemas)

    except Exception as e:
        return f"❌ 检索数据字典失败: {str(e)}"
    finally:
        # 保持连接池整洁
        try:
            connections.disconnect("default")
        except:
            pass

def generate_sql(query: str) -> str:
    """
    根据用户查询和表格 schema 信息生成 SQL 语句
    """
    try:
        # 获取相关的表结构信息
        schema_info = get_table_schema(query)

        if "未在数据字典中找到匹配的表结构" in schema_info:
            return schema_info

        # 构建提示词，让 LLM 生成正确的 SQL
        prompt = f"""
        根据以下表结构信息和用户查询，生成正确的 SQL 语句：

        表结构信息：
        {schema_info}

        用户查询：
        {query}

        请生成合适的 SQL 语句来满足用户的需求。如果涉及多个表的关联查询，请确保：
        1. 使用正确的 JOIN 语法
        2. 使用正确的表别名
        3. 包含必要的连接条件
        4. 确保 SELECT 字段正确
        5. 添加适当的 WHERE 条件

        请只返回 SQL 语句，不要添加任何解释说明。
        """

        # 使用 Ollama 生成 SQL
        response = ollama.generate(
            model="llama3.2:1b",
            prompt=prompt,
            stream=False
        )

        sql = response['response'].strip()

        # 清理 SQL，确保只返回 SQL 语句
        # 移除可能的代码块标记
        sql = re.sub(r'^```.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'^```sql.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'^```.*$', '', sql, flags=re.MULTILINE)
        sql = sql.strip()

        return sql

    except Exception as e:
        return f"❌ 生成 SQL 语句失败: {str(e)}"

def table_schema_query_skill(query: str) -> str:
    """
    表格关联查询技能入口函数

    参数:
    - query: 用户的查询问题

    返回:
    - 包含表结构信息和生成的 SQL 语句
    """
    # 先获取表结构信息
    schema_info = get_table_schema(query)

    # 再生成 SQL
    sql = generate_sql(query)

    return f"表结构信息:\n{schema_info}\n\n生成的 SQL 语句:\n{sql}"

# 为技能系统提供接口
if __name__ == "__main__":
    # 测试示例
    print("测试用户查询: 统计越南用户的订单总额需要哪些表？")
    result = table_schema_query_skill("统计越南用户的订单总额需要哪些表？")
    print(result)