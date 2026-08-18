# TicketRAGAgent
RAG-powered support ticket knowledge agent

前端--》搜索--》向量数据库--》找到相似的产品--》使用promptemplate--》添加输入变量组装prompt--》交给llm --》生成想要的答案或总结--》返回给前端
## Agent
准备数据：
导入数据csv数据--》pandas 数据整理清理特性--》向量嵌入--》weaviate向量数据库
|
|
v
使用weaviateSDK相关方法--》查询数据--》》提供查询接口
|
|
v
提供查询接口--》使用prompttemplate--》组装查询数据--》交给llm（langchian）--》生成想要的答案或总结 --》返回给server


## 搜索
问题 --》向量化--》生成查询向量 --》在weaviate中搜索 --》转成document 返回


## LCEL 问答链
输入处理--》提示词模版--》LLM调用 --》输出解析（通过管道操作 | 串起整个流程）
典型的rag（检索增强生成）模式生成


## 统一返回格式
- code： 业务状态码（ 0 = 成功， 2000-2999 = agent错误）
- msg：提示信息
- data：业务数据

## frontend
Next.js / React / ReactNative + TailwindCSS
    |
    | HTTP/HTTPS
    | SSE (Server-Sent Events)
    v

## server
FastAPI + SQLAlchemy + Redis + PGSQL / JWT + CORS
    |
    | HTTP
    | SSE (Server-Sent Events)
    v
## agent
LangChain + Ollama + Weaviate  + Pandas



