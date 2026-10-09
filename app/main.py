from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.routers import requests, reports, ui

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IT Service Request Management")

app.include_router(requests.router)
app.include_router(reports.router)
app.include_router(ui.router, include_in_schema=False)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "details": exc.errors()}
    )


@app.get("/health")
def health():
    return {"status": "ok"}