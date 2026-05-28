from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from src.endpoints import chat_router as chat_v1
from fastapi.staticfiles import StaticFiles
from src.endpoints import ws_router as ws_1
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
import time
import httpx
import os
from connections.dbconn import pg_pool, connection


@asynccontextmanager
async def lifespan (app: FastAPI):
    try:
        conn = pg_pool.getconn()
        pg_pool.putconn(conn)
        print("✅ Postgres pool ready")
    except Exception as e:
        raise RuntimeError(f"❌ Postgres not available: {e}")

    yield

    pg_pool.closeall()
    print("🔴 Postgres pool closed")


def create_application() -> FastAPI:
    application = FastAPI(
        title="Chat platform",
        description="Chat Service",
        version="1.0.0",
        openapi_url="/chats/openapi.json",
        docs_url="/chats/docs")
    application.include_router(chat_v1.router, prefix='/chats')
    application.include_router(ws_1.router, prefix='/chats')

    return application

app = create_application()

app.mount('/static', StaticFiles(directory='static'), 'static')


app.add_middleware(
    CORSMiddleware,
    allow_origins='*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response.headers["X-Process-App"] = "Time took to process the request and return response is {} sec".format(time.time() - start_time)
    return response


@app.get('/')
def index():
    return RedirectResponse("/chats/docs")

@app.get("/health")
async def health_check():
    health_status = {
        "status": "ok",
        "database": "down"
    }
    overall_healthy = True

    try:
        with connection() as cur:
            cur.execute("SELECT 1")
            if cur.fetchone():
                health_status["database"] = "up"
    except Exception as e:
        health_status["status"] = "error"
        overall_healthy = False
        print(f"HealthCheck Database Error: {e}")

    import httpx

# ... внутри вашей функции healthcheck ...
    try:
        # MinIO по умолчанию отдает 200 OK на /minio/health/live
        minio_url = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{minio_url}/minio/health/live", timeout=5)
            
        if response.status_code == 200:
            health_status["minio"] = "up"
        else:
            overall_healthy = False
            health_status["minio"] = f"down: Status {response.status_code}"
    except Exception as e:
        overall_healthy = False
        health_status["minio"] = f"down: {type(e).__name__}"
    return health_status

