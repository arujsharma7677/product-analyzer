from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect, disconnect
from app.routes import auth, analyse, credits

app = FastAPI(title="Product Analyser API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await connect()

@app.on_event("shutdown")
async def shutdown():
    await disconnect()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(analyse.router, prefix="/api", tags=["Analyse"])
app.include_router(credits.router, prefix="/api", tags=["Credits"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "Product Analyser API running"}
