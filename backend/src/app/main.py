from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.app.api import api_router 

app = FastAPI()

# CORS setup — adjust origins as needed
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routes
app.include_router(api_router)
