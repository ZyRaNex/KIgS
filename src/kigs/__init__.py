import uvicorn
from fastapi import FastAPI

from .read_routes import router as read_router
from .write_routes import router as write_router

app = FastAPI()
app.include_router(read_router)
app.include_router(write_router)


def main() -> None:
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        loop="asyncio",
        http="zttp",
    )
