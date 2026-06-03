import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal
from app.routers import admin, alerts, auth, hosts, metrics, network, ws
from app.services.log_service import record_log
from app.utils.bootstrap import init_database


settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    try:
        with SessionLocal() as db:
            init_database(db)
    except Exception:
        logger.exception("Application startup failed")
        raise


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled API exception", exc_info=(type(exc), exc, exc.__traceback__))
    try:
        with SessionLocal() as db:
            record_log(
                db,
                "error",
                "api",
                "Unhandled API exception",
                source=str(request.url.path),
                details={"error": str(exc)},
            )
            db.commit()
    except Exception:
        logger.exception("Failed to write API exception to system log")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router, prefix="/api")
app.include_router(hosts.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(network.router, prefix="/api")
app.include_router(ws.router)
