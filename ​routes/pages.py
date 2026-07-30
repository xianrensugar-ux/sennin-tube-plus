import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import INVIDIOUS_INSTANCES, PIPED_INSTANCES, COBALT_INSTANCES, client_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/status", response_class=HTMLResponse)
async def read_status(request: Request):
    """すべての接続先 API（Invidious, Piped, Cobalt）の遅延と稼働状況をチェック"""
    async def check_api(instance_url: str, endpoint: str, api_type: str):
        start_time = asyncio.get_event_loop().time()
        try:
            resp = await client_session.get(f"{instance_url.rstrip('/')}{endpoint}", timeout=3.0)
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            if resp.status_code in [200, 204]:
                return {
                    "type": api_type,
                    "instance": instance_url,
                    "status": "Online",
                    "latency": f"{int(latency)}ms"
                }
            return {"type": api_type, "instance": instance_url, "status": f"HTTP {resp.status_code}", "latency": "-"}
        except Exception:
            return {"type": api_type, "instance": instance_url, "status": "Offline", "latency": "-"}

    tasks = []
    for inst in INVIDIOUS_INSTANCES:
        tasks.append(check_api(inst, "/api/v1/stats", "Invidious"))
    for inst in PIPED_INSTANCES:
        tasks.append(check_api(inst, "/config", "Piped"))
    for inst in COBALT_INSTANCES:
        tasks.append(check_api(inst, "/api/serverinfo", "Cobalt"))

    results = await asyncio.gather(*tasks)
    return templates.TemplateResponse("status.html", {"request": request, "instances": results})

# 静的コンテンツ用ルート
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
