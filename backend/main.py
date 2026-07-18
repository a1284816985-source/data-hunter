"""
多平台数据猎手 — FastAPI 主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, engine
from api import tasks, data, reports, auth, accounts

app = FastAPI(title="数据猎手 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks.router, prefix="/api/tasks", tags=["采集任务"])
app.include_router(data.router, prefix="/api/data", tags=["数据浏览"])
app.include_router(reports.router, prefix="/api/reports", tags=["AI报告"])
app.include_router(auth.router, prefix="/api/auth", tags=["登录"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["平台账号"])


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "data-hunter"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8765, reload=True)
