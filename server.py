import math
import os
import threading
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from matching_engine import MatchingEngine

app = FastAPI(title="ChronosMatch Matching Engine API", version="1.0.0")
engine = MatchingEngine(capacity=10000)
engine_lock = threading.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chronosmatch-live.hatchable.site",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class OrderRequest(BaseModel):
    side: Literal["BUY", "SELL"]
    price: int = Field(gt=0, description="Integer price units")
    quantity: int = Field(gt=0, description="Positive whole-number quantity")

@app.get("/")
def root():
    return {"service": "ChronosMatch API", "status": "ok", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy", "engine": "cython", "service": "chronosmatch"}

@app.get("/api/stats")
def get_stats():
    with engine_lock:
        return engine.stats()

@app.get("/api/orderbook")
def get_orderbook():
    with engine_lock:
        return {"orders": engine.snapshot(), "stats": engine.stats()}

@app.post("/api/orders")
def submit_order(order: OrderRequest):
    side_code = 1 if order.side == "BUY" else -1
    try:
        with engine_lock:
            result = engine.submit(side_code, order.price, order.quantity)
            return {
                "order": result,
                "stats": engine.stats(),
                "orders": engine.snapshot(),
            }
    except (ValueError, OverflowError, MemoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Keep internal implementation details out of the HTTP response.
        raise HTTPException(status_code=500, detail="Order submission failed") from exc
