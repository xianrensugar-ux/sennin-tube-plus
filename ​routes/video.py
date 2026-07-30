import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx

from config import INVIDIOUS_INSTANCES, PIPED_INSTANCES, COBALT_INSTANCES, client_session
from utils.cache import search_cache
from utils.fetcher import fetch_invidious, fetch_video_ultra, fetch_cobalt_stream

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.add_extension('jinja2.ext.do')

@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = Query(...), page: int = 1, type: str = "video", force_instance: str = Query(None)):
    cache_key = f"search:{q}:{type}:{page}"
    cached_results = await search_cache.get(cache_key)
    if cached_results:
        return templates.TemplateResponse("search.html", {
            "request": request, "query": q, "results": cached_results, "type": type, "page": page
        })

    try:
        search_type = type if type != "short" else "video"
        query_q = q if type != "short" else f"{q} shorts"
        params = {"q": query_q, "page": page, "type": search_type}

        data = await fetch_invidious("/search", params, force_instance=force_instance)

        results = [{
            "type": item.get("type"),
            "videoId": item.get("videoId"),
            "playlistId": item.get("playlistId"),
            "authorId": item.get("authorId"),
            "title": item.get("title"),
            "lengthSeconds": item.get("lengthSeconds"),
            "author": item.get("author"),
            "authorThumbnails": item.get("authorThumbnails"),
            "videoThumbnails": item.get("videoThumbnails"),
            "viewCountText": item.get("viewCountText"),
            "viewCount": item.get("viewCount"),
            "publishedText": item.get("publishedText"),
            "subCountText": item.get("subCountText"),
            "videoCount": item.get("videoCount")
        } for item in data]

        await search_cache.set(cache_key, results)

        return templates.TemplateResponse("search.html", {
            "request": request, "query": q, "results": results, "type": type, "page": page
        })
    except httpx.TimeoutException:
        return templates.TemplateResponse("apitimeout.html", {"request": request})
    except Exception:
        return templates.TemplateResponse("apiallerror.html", {"request": request, "instances": INVIDIOUS_INSTANCES})

@router.get("/watch", response_class=HTMLResponse)
async def watch(request: Request, v: str = Query(...), force_instance: str = Query(None)):
    try:
        # 動画本体とコメントを非同期並列で取得
        video_task = fetch_video_ultra(v, force_instance=force_instance)
        comment_task = fetch_invidious(f"/comments/{v}", force_instance=force_instance)

        video_data, comment_data = await asyncio.gather(video_task, comment_task, return_exceptions=True)

        if isinstance(video_data, Exception):
            raise video_data

        adaptive = video_data.get("adaptiveFormats", [])
        
        audio_url = None
        for f in adaptive:
            if "audio" in f.get("type", ""):
                if f.get("language") == "ja":
                    audio_url = f.get("url")
                    break
        if not audio_url and adaptive:
            audio_url = next((f.get("url") for f in adaptive if "audio" in f.get("type", "")), None)

        format_streams = video_data.get("formatStreams", [])

        stream_urls = [{
            "url": fmt.get("url"),
            "resolution": fmt.get("qualityLabel"),
            "format": "mp4/mixed",
            "audioUrl": ""
        } for fmt in format_streams]

        stream_urls.extend({
            "url": fmt.get("url"),
            "resolution": fmt.get("qualityLabel"),
            "format": "webm/videoOnly",
            "audioUrl": audio_url
        } for fmt in adaptive if "video" in fmt.get("type", "") and "webm" in fmt.get("container", ""))

        video_urls = [fmt.get("url") for fmt in format_streams] or \
                     [fmt.get("url") for fmt in adaptive if "video" in fmt.get("type", "")]

        recommended = [{
            "video_id": rec.get("videoId"),
            "title": rec.get("title"),
            "author": rec.get("author"),
            "view_count_text": rec.get("viewCountText")
        } for rec in video_data.get("recommendedVideos", [])]

        author_thumbs = video_data.get("authorThumbnails", [])
        author_icon = author_thumbs[-1]["url"] if author_thumbs else ""

        response = templates.TemplateResponse("watch.html", {
            "request": request,
            "videoid": v,
            "video_title": video_data.get("title"),
            "videourls": video_urls,
            "streamUrls": stream_urls,
            "author": video_data.get("author"),
            "author_id": video_data.get("authorId"),
            "author_icon": author_icon,
            "subscribers_count": video_data.get("subCountText", "非公開"),
            "view_count": video_data.get("viewCount", 0),
            "like_count": video_data.get("likeCount", 0),
            "description": video_data.get("descriptionHtml", "").replace("\n", "<br>"),
            "recommended_videos": recommended,
            "comments": comment_data.get("comments", []) if not isinstance(comment_data, Exception) else [],
            "youtube_url": f"https://www.youtube.com/watch?v={v}"
        })

        # Cookie 履歴更新
        try:
            history_json = request.cookies.get("history", "[]")
            history = json.loads(history_json)
            history = [item for item in history if item.get("videoId") != v]
            history.append({
                "videoId": v,
                "title": video_data.get("title"),
                "author": video_data.get("author"),
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            if len(history) > 50: history = history[-50:]
            response.set_cookie(key="history", value=json.dumps(history), max_age=2592000, httponly=True)
        except Exception:
            pass

        return response
    except httpx.TimeoutException:
        return templates.TemplateResponse("apitimeout.html", {"request": request})
    except Exception:
        return templates.TemplateResponse("apiallerror.html", {"request": request, "instances": INVIDIOUS_INSTANCES})

# 新機能: Cobalt API ダイレクトダウンロード/高画質ストリームエンドポイント
@router.get("/api/cobalt/{v}")
async def cobalt_api_endpoint(v: str):
    data = await fetch_cobalt_stream(v)
    if data:
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "Cobalt extraction failed"}, status_code=500)

@router.get("/shorts/{v}", response_class=HTMLResponse)
async def shorts_player(request: Request, v: str, force_instance: str = Query(None)):
    return await watch(request, v=v, force_instance=force_instance)

@router.get("/suggest")
async def suggest(keyword: str):
    """YouTube公式補完API + Invidious の並列フォールバックサジェスト"""
    # 1. YouTube 公式 Suggest API (最速)
    try:
        yt_suggest_url = f"https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&q={keyword}"
        resp = await client_session.get(yt_suggest_url, timeout=1.2)
        if resp.status_code == 200:
            # 形式: window.google.ac.h(["q",[["sugg1",0],["sugg2",0]]])
            text = resp.text
            start = text.find("(") + 1
            end = text.rfind(")")
            data = json.loads(text[start:end])
            return [item[0] for item in data[1]]
    except Exception:
        pass

    # 2. Invidious 並列フォールバック
    urls = [f"{inst.rstrip('/')}/api/v1/search/suggestions" for inst in INVIDIOUS_INSTANCES[:3]]
    tasks = [asyncio.create_task(client_session.get(u, params={"q": keyword})) for u in urls]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending: t.cancel()
    for t in done:
        try:
            r = t.result()
            if r.status_code == 200:
                return r.json().get("suggestions", [])
        except Exception:
            continue
    return []

@router.get("/proxy/thumb")
async def proxy_thumb(v: str):
    thumb_url = f"https://i.ytimg.com/vi/{v}/mqdefault.jpg"
    try:
        resp = await client_session.get(thumb_url, timeout=3.0)
        return Response(content=resp.content, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        return Response(status_code=404)

@router.get("/thumbnail")
async def thumbnail(v: str):
    return await proxy_thumb(v)
