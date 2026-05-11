import argparse
from fastapi.staticfiles import StaticFiles
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.scripts.seed_analysis_methods import seed_methods
from app.config import settings
from app.api.routes import (
    analysis,
    file_info,
    health,
    upload,
    preprocess,
    visualization,
    ai_models,
    database,
    pipelines,
    system,
)

from app.core.model_registry import get_models_dir
from app.db import init_db
from app.db.migration import upgrade_db

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.mount("/api/static/models", StaticFiles(directory=get_models_dir()), name="model_assets")

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(database.router, prefix="/api", tags=["Database"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(file_info.router, prefix="/api", tags=["File Info"])
app.include_router(preprocess.router, prefix="/api", tags=["Preprocess"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(visualization.router, prefix="/api", tags=["Visualization"])
app.include_router(pipelines.router, prefix="/api", tags=["Pipelines"])
app.include_router(ai_models.router, prefix="/api", tags=["AI Models"])


@app.on_event("startup")
def startup():
    engine = init_db(app_name="MyEEGApp")
    upgrade_db(engine)
    seed_methods()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, use_colors=False)
