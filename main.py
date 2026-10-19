"""FastAPI 应用入口。"""

from fastapi import FastAPI

from app.api.lifespan import lifespan
from app.api.middleware import RequestIDMiddleware
from app.api.routers.query_router import query_router

app = FastAPI(
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)

app.include_router(query_router)
