from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine
from .routers import auth, billing, jobs, admin, config_public
from .config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(config_public.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def index():
    return FileResponse("app/templates/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
