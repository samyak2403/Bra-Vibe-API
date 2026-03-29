from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

RAPIDAPI_PROXY_SECRET = os.getenv("RAPIDAPI_PROXY_SECRET")

app = FastAPI(
    title="Bra Vibe India Deals API",
    description="REST API for aggregated lingerie discounts across Indian e-commerce stores.",
    version="1.0.0"
)

# Enable CORS for the existing website and RapidAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "bras_deals.json")
PREMIUM_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "premium_bras.json")

class Deal(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    price_original: float
    price_discounted: float
    discount_percentage: int
    image_url: str
    product_url: str
    website_source: str
    stock_status: str
    scraped_at: str

class APIResponse(BaseModel):
    metadata: Dict[str, Any]
    deals: List[Deal]

def load_data(is_premium: bool = False):
    target_file = PREMIUM_DATA_FILE if is_premium else DATA_FILE
    if not os.path.exists(target_file):
        return {"metadata": {}, "deals": []}
    with open(target_file, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.get("/", tags=["General"])
async def root():
    return {
        "message": "Welcome to Bra Vibe API",
        "docs": "/docs",
        "status": "active"
    }

@app.get("/deals", response_model=APIResponse, tags=["Deals"])
async def get_deals(
    brand: Optional[str] = Query(None, description="Filter by brand name (case-insensitive)"),
    source: Optional[str] = Query(None, description="Filter by website source (e.g. Amazon India)"),
    min_discount: Optional[int] = Query(20, description="Minimum discount percentage"),
    rapidapi_proxy_secret: Optional[str] = Header(None, alias="X-RapidAPI-Proxy-Secret")
):
    """
    Retrieve all current deals with optional filtering. 
    Securely validated via RapidAPI Proxy Secret if configured.
    """
    if RAPIDAPI_PROXY_SECRET and rapidapi_proxy_secret != RAPIDAPI_PROXY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid RapidAPI Proxy Secret")

    data = load_data(is_premium=False)
    deals = data.get("deals", [])
    
    # Filtering logic
    if brand:
        deals = [d for d in deals if brand.lower() in d['brand'].lower()]
    if source:
        deals = [d for d in deals if source.lower() in d['website_source'].lower()]
    if min_discount:
        deals = [d for d in deals if d['discount_percentage'] >= min_discount]
        
    return {
        "metadata": data.get("metadata", {}),
        "deals": deals
    }

@app.get("/premium-deals", response_model=APIResponse, tags=["Deals"])
async def get_premium_deals(
    brand: Optional[str] = Query(None, description="Filter by brand name (case-insensitive)"),
    source: Optional[str] = Query(None, description="Filter by website source (e.g. Amazon India)"),
    min_discount: Optional[int] = Query(20, description="Minimum discount percentage"),
    rapidapi_proxy_secret: Optional[str] = Header(None, alias="X-RapidAPI-Proxy-Secret")
):
    """
    Retrieve all premium-brand lingerie deals with optional filtering. 
    Securely validated via RapidAPI Proxy Secret if configured.
    """
    if RAPIDAPI_PROXY_SECRET and rapidapi_proxy_secret != RAPIDAPI_PROXY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid RapidAPI Proxy Secret")

    data = load_data(is_premium=True)
    deals = data.get("deals", [])
    
    # Filtering logic
    if brand:
        deals = [d for d in deals if brand.lower() in d['brand'].lower()]
    if source:
        deals = [d for d in deals if source.lower() in d['website_source'].lower()]
    if min_discount:
        deals = [d for d in deals if d['discount_percentage'] >= min_discount]
        
    return {
        "metadata": data.get("metadata", {}),
        "deals": deals
    }

@app.get("/brands", tags=["Metadata"])
async def get_brands():
    """Get a list of all unique brands in the current deal set."""
    data = load_data()
    brands = sorted(list(set(d['brand'] for d in data.get("deals", []))))
    return {"brands": brands}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
