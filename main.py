"""FastAPI启动入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.api.rate_limit import RateLimitMiddleware
from src.config import API_HOST, API_PORT

app = FastAPI(
    title="RAG智能问答API",
    description="基于个人知识库的智能问答服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加限流中间件
app.add_middleware(RateLimitMiddleware)

# 挂载路由
app.include_router(router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "RAG智能问答API",
        "docs": "/docs",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
