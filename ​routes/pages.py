import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import INVIDIOUS_INSTANCES, client_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/games", response_class=HTMLResponse)
async def read_games(request: Request): return templates.TemplateResponse("games.html", {"request": request})

@router.get("/block.html", response_class=HTMLResponse)
async def read_block(request: Request): return templates.TemplateResponse("block.html", {"request": request})

@router.get("/tumu.html", response_class=HTMLResponse)
async def read_tumu(request: Request): return templates.TemplateResponse("tumu.html", {"request": request})

@router.get("/2048.html", response_class=HTMLResponse)
async def read_2048(request: Request): return templates.TemplateResponse("2048.html", {"request": request})

@router.get("/subscriptions", response_class=HTMLResponse)
async def subscriptions_page(request: Request): return templates.TemplateResponse("subscriptions.html", {"request": request})

@router.get("/bbs", response_class=HTMLResponse)
async def bbs_page(request: Request): return templates.TemplateResponse("bbs.html", {"request": request})

@router.get("/ytdl", response_class=HTMLResponse)
async def ytdl_page(request: Request): return templates.TemplateResponse("bbs.html", {"request": request})

@router.get("/status", response_class=HTMLResponse)
async def read_status(request: Request):
    async def check_instance(instance):
        start_time = asyncio.get_event_loop().time()
        try:
            resp = await client_session.get(f"{instance.rstrip('/')}/api/v1/stats", timeout=4.0)
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "instance": instance,
                    "status": "Online",
                    "latency": f"{int(latency)}ms",
                    "version": data.get("software", {}).get("version", "unknown"),
                    "users": data.get("usage", {}).get("users", {}).get("total", 0)
                }
            return {"instance": instance, "status": f"Error {resp.status_code}", "latency": "-", "version": "-", "users": "-"}
        except Exception:
            return {"instance": instance, "status": "Offline", "latency": "-", "version": "-", "users": "-"}

    status_results = await asyncio.gather(*(check_instance(inst) for inst in INVIDIOUS_INSTANCES))
    return templates.TemplateResponse("status.html", {"request": request, "instances": status_results})
