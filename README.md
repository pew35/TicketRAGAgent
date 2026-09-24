# TicketRAGAgent
RAG-powered support ticket knowledge agent

## Public Demo Deployment

The repository includes a cloud deployment mode that keeps the complete user
flow available without requiring a visitor to run Ollama or Weaviate:

- GitHub stores the source and publishes the React frontend with GitHub Pages.
- Render runs the FastAPI API, authentication, chat history, and in-process RAG.
- Neon (or another hosted PostgreSQL provider) stores users and conversations.
- OpenRouter supplies the hosted language model. The default model is the free
  `openrouter/free` router.

The same Render URL also serves the frontend, so the application remains usable
even before GitHub Pages is enabled.

### Deploy

1. Create a PostgreSQL database and copy its connection string.
2. Create an OpenRouter API key.
3. In Render, create a Blueprint from this GitHub repository. Render reads
   `render.yaml`; enter the database connection string for
   `SERVER_DATABASE_URL` and the OpenRouter key for `SERVER_LLM_API_KEY`.
4. Wait for `/health` to report a successful deployment. Render runs Alembic
   migrations automatically before starting the API.
5. In GitHub, open **Settings > Secrets and variables > Actions > Variables**
   and create `API_BASE_URL` with the Render URL, such as
   `https://ticket-rag-agent.onrender.com`.
6. Open **Settings > Pages**, choose **GitHub Actions** as the source, and run
   the `Deploy frontend to GitHub Pages` workflow.

The public Pages URL will be
`https://<github-user>.github.io/<repository>/`. Free Render services sleep
after inactivity, so the first request after a quiet period can take about one
minute.

### Cloud environment variables

| Variable | Purpose |
| --- | --- |
| `SERVER_DATABASE_URL` | Hosted PostgreSQL connection string |
| `SERVER_LLM_API_KEY` | OpenRouter API key |
| `SERVER_LLM_MODEL` | Defaults to `openrouter/free` |
| `SERVER_AGENT_MODE` | Use `internal` for the public demo |
| `SERVER_REDIS_ENABLED` | Use `false` for the public demo |

Never commit API keys or database passwords. Render stores these values as
secret environment variables.

## System Overview

```text
┌──────────────────────────────────────────────────────────────┐
│                        TicketRAGAgent                         │
│        Customer Support RAG System for E-commerce Tickets      │
└──────────────────────────────────────────────────────────────┘

        ┌──────────────┐
        │   Frontend   │
        │   Chat UI    │
        └──────┬───────┘
               │ HTTP / SSE
               ▼
┌──────────────────────────────────────────────────────────────┐
│                         Server API                            │
│                     FastAPI Backend                           │
├──────────────────────────────────────────────────────────────┤
│  Auth        │ JWT login / refresh / current user              │
│  Users       │ Register, login, profile, admin user APIs       │
│  Chats       │ Conversations, messages, history persistence    │
│  Monitoring  │ Health, readiness, runtime checks               │
└──────────────┬───────────────────────────┬───────────────────┘
               │                           │
               ▼                           ▼
     ┌──────────────────┐        ┌──────────────────┐
     │    PostgreSQL    │        │      Redis       │
     │  Users / Chats   │        │ Cache / Sessions │
     └──────────────────┘        └──────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│                       Agent Service                           │
│                  FastAPI RAG HTTP Service                     │
├──────────────────────────────────────────────────────────────┤
│  1. Validate question                                          │
│  2. Create embedding                                           │
│  3. Search similar service tickets                             │
│  4. Build prompt context                                       │
│  5. Stream or return final answer                              │
└──────────────┬───────────────────────────┬───────────────────┘
               │                           │
               ▼                           ▼
     ┌──────────────────┐        ┌──────────────────┐
     │      Ollama      │        │     Weaviate     │
     │ LLM + Embedding  │        │ Vector Database  │
     └──────────────────┘        └──────────────────┘
```

## Project Structure

```text
TicketRAGAgent
├─ frontend
│  └─ Customer support chat interface
│
├─ server
│  ├─ server
│  │  ├─ web/api
│  │  │  ├─ users          Login, register, token refresh, user APIs
│  │  │  ├─ conversations  Chat history, messages, agent streaming
│  │  │  ├─ monitoring     Health and readiness checks
│  │  │  └─ docs           Swagger and ReDoc routes
│  │  │
│  │  ├─ models            SQLAlchemy ORM models
│  │  ├─ dao               Database access layer
│  │  ├─ utils             JWT and helper utilities
│  │  ├─ auth.py           Auth dependencies
│  │  ├─ settings.py       Environment configuration
│  │  └─ main.py           FastAPI application entry
│  │
│  └─ deploy               Docker Compose for PostgreSQL and Redis
│
└─ agent
   ├─ agent
   │  ├─ ticket_agent.py   RAG workflow orchestration
   │  ├─ config.py         Model, prompt, and retrieval config
   │  ├─ response.py       Agent events, responses, and error codes
   │  └─ import_data.py    Load ticket CSV into vector database
   │
   ├─ data
   │  └─ service_tickets.csv
   │
   └─ http_service.py      FastAPI wrapper around the RAG agent
```

## Request Flow

```text
User Question
     │
     ▼
Frontend Chat UI
     │
     │  POST /api/conversations/{id}/messages/stream
     ▼
Server Conversation API
     │
     ├─ Save user message
     ├─ Create agent_run record
     │
     ▼
Agent HTTP Service
     │
     ├─ Embed question with Ollama
     ├─ Search similar tickets in Weaviate
     ├─ Build prompt with retrieved context
     └─ Generate answer with LLM
     │
     ▼
Server Conversation API
     │
     ├─ Save assistant message
     ├─ Update conversation title
     └─ Return code / message / data or SSE events
     │
     ▼
Frontend renders answer
```

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
- message：提示信息
- data：业务数据


## Server
- FastAPI - 现代化异步 web框架 支持sse
- sqlalchemy 2.0 异步 ORM 支持 prstgresSQL
- redis 缓存支持 提升相应速度
- JWT 认证系统， 保障接口安全
- loguru 结构化日志， 便于问题追踪
- docker 数据库容器化， 简化部署
- Alembic 数据库迁移

