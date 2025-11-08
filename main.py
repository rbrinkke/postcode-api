import logging
import os
import sys
import time
import aiosqlite
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pythonjsonlogger import jsonlogger
from starlette.types import ASGIApp, Receive, Scope, Send, Message

# Configure structured JSON logging
def setup_logging():
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler for Docker
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Suppress uvicorn access logs (we'll use our own middleware)
    logging.getLogger("uvicorn.access").disabled = True
    
    return logging.getLogger(__name__)

logger = setup_logging()

# Response model
class PostcodeResponse(BaseModel):
    postcode: str = Field(..., description="Dutch postcode (e.g., 1012AB)")
    lat: float = Field(..., description="Latitude in WGS84")
    lon: float = Field(..., description="Longitude in WGS84") 
    woonplaats: str = Field(..., description="City/town name")

# Database configuration (can be overridden with DB_PATH environment variable)
DB_PATH = os.getenv("DB_PATH", "/opt/postcode/geodata/bag.sqlite")

# Pure ASGI middleware for logging (NOT BaseHTTPMiddleware!)
class LoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        path = scope.get("path", "")
        method = scope.get("method", "")
        
        # Skip logging for health checks
        if path != "/health":
            self.logger.info("Request started", extra={
                "method": method,
                "path": path
            })
        
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                process_time = time.time() - start_time
                if path != "/health":
                    status_code = message.get("status", 0)
                    self.logger.info("Request completed", extra={
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "process_time_ms": round(process_time * 1000, 2)
                    })
            await send(message)
        
        await self.app(scope, receive, send_wrapper)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting postcode API", extra={"db_path": DB_PATH})
    
    # Test database connection
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM nums") as cursor:
                count = await cursor.fetchone()
                logger.info("Database connected", extra={"address_count": count[0]})
    except Exception as e:
        logger.error("Database connection failed", extra={"error": str(e)})
        raise
    
    yield
    
    logger.info("Shutting down postcode API")

# Create FastAPI app
app = FastAPI(
    title="Postcode API",
    description="Fast postcode to GPS coordinate lookup for Dutch postcodes",
    version="1.0.0",
    lifespan=lifespan
)

# Add our custom middleware
app.add_middleware(LoggingMiddleware)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )

@app.get("/postcode/{postcode}", response_model=PostcodeResponse)
async def get_postcode(postcode: str):
    """
    Get GPS coordinates and city for a Dutch postcode
    
    - **postcode**: Dutch postcode without spaces (e.g., 1012AB)
    """
    # Normalize postcode: uppercase, no spaces
    postcode = postcode.upper().strip().replace(" ", "")
    
    # Basic validation
    if len(postcode) != 6 or not (postcode[:4].isdigit() and postcode[4:].isalpha()):
        logger.warning("Invalid postcode format", extra={"postcode": postcode})
        raise HTTPException(
            status_code=400,
            detail=f"Invalid postcode format: {postcode}. Expected format: 1234AB"
        )
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT postcode, lat, lon, woonplaats FROM unilabel WHERE postcode = ? LIMIT 1",
                (postcode,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    logger.info("Postcode not found", extra={"postcode": postcode})
                    raise HTTPException(
                        status_code=404,
                        detail=f"Postcode {postcode} not found in database"
                    )
                
                logger.info("Postcode found", extra={
                    "postcode": postcode,
                    "lat": row[1],
                    "lon": row[2],
                    "woonplaats": row[3]
                })
                
                return PostcodeResponse(
                    postcode=row[0],
                    lat=row[1],
                    lon=row[2],
                    woonplaats=row[3]
                )
                
    except aiosqlite.Error as e:
        logger.error("Database error", extra={"error": str(e), "postcode": postcode})
        raise HTTPException(
            status_code=500,
            detail="Database error occurred"
        )