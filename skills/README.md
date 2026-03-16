# Skills 文件夹

这个文件夹包含了所有Dofi Agent的技能模块。每个技能都是一个独立的Python文件，负责特定的功能。

## 技能说明

- `docker_management.py` - Docker容器管理技能，用于查看、启动、停止和重启容器
- `docker_management_skill.py` - Docker技能的包装器，用于在Agent中调用
- `knowledge_retrieval.py` - 知识检索技能，用于从知识库中检索信息
- `milvus_memory_skill.py` - Milvus内存管理技能，用于处理向量数据库相关操作
- `table_schema_retrieval.py` - 表结构检索技能，用于获取数据库表结构信息
- `mac_automation.py` - macOS自动化技能，用于执行macOS系统相关操作
- `time_utils.py` - 时间工具技能，提供时间处理相关功能

## 使用方法

技能通过Agent的技能加载系统自动加载。每个技能都应遵循统一的接口规范，以便在Agent中正确调用。