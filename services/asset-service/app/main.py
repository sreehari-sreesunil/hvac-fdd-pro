from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import Base, engine
from app.models import asset  # noqa: F401
from app.routers import asset_types, assets, facilities
from common.logging_config import configure_logging

configure_logging("asset-service")

app = FastAPI(title="asset-service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "asset-service"}


app.include_router(facilities.router)
app.include_router(asset_types.router)
app.include_router(assets.router)
