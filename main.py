from fastapi import FastAPI
from src.routes import router

app = FastAPI(title="APITestify Python Middleware")
app.include_router(router)
