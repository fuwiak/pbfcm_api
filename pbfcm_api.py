# pbfcm_api.py
# FastAPI endpoint for PBFCM tax sale list (perfect for n8n)
# GET /pbfcm/scrape → returns { source_url, count, raw[], normalized[] }

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from pbfcm_engine import PBFcmsScraper

app = FastAPI(title="PBFCM taxsale scraper", default_response_class=ORJSONResponse)

scraper = PBFcmsScraper(headless=True)

@app.on_event("startup")
async def _startup():
    await scraper.start()

@app.on_event("shutdown")
async def _shutdown():
    await scraper.stop()

@app.get("/pbfcm/health")
async def health():
    return {"ok": True}

@app.get("/pbfcm/scrape")
async def scrape():
    data = await scraper.scrape()
    return data
