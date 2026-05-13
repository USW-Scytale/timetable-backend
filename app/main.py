from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import validation_exception_handler, http_exception_handler
from app.database import engine
from app.models import Base
from app.routers import auth, departments, students, timetables, rooms, graduation, courses


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="수원대 스마트 시간표 API",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(students.router)
app.include_router(timetables.router)
app.include_router(rooms.router)
app.include_router(graduation.router)
app.include_router(courses.router)


@app.get("/health")
def health():
    return {"status": "ok"}
