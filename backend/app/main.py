from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import ws_routes
from app.routes.post_routes import router as post_router
from app.routes.thread_routes import router as thread_router
from app.routes.user_routes import router as user_router
from app.utils.redis_notifications import start_redis_listener, stop_redis_listener

app = FastAPI()

welcome_router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/debug/headers")
async def debug_headers(request: Request):
    return dict(request.headers)


@app.get("/")
async def welcome():
    return {
        "message": "Welcome to Realtime Discussion Forum Web",
        "API docs": "/docs",
        "API redoc": "/redoc",
    }


app.include_router(user_router, prefix="/users")
app.include_router(thread_router, prefix="/threads")
app.include_router(post_router, prefix="/posts")
app.include_router(ws_routes.router, prefix="")


@app.on_event("startup")
async def startup_event():
    # start redis listener if REDIS_URL is configured
    redis_url = getattr(settings, "REDIS_URL", None)
    if redis_url:
        await start_redis_listener(redis_url)


@app.on_event("shutdown")
async def shutdown_event():
    await stop_redis_listener()
