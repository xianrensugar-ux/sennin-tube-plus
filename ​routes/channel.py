from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

from config import INVIDIOUS_INSTANCES
from utils.fetcher import fetch_invidious

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.add_extension('jinja2.ext.do')

@router.get("/channel/{ucid}", response_class=HTMLResponse)
async def channel(request: Request, ucid: str, sort_by: str = "newest", tab: str = "videos", force_instance: str = Query(None)):
    try:
        channel_data = await fetch_invidious(f"/channels/{ucid}", force_instance=force_instance)
        
        tab_task = None
        if tab == "videos":
            tab_task = fetch_invidious(f"/channels/{ucid}/videos", {"sort_by": sort_by}, force_instance=force_instance)
        elif tab == "shorts":
            tab_task = fetch_invidious(f"/channels/{ucid}/shorts", force_instance=force_instance)
        elif tab == "playlists":
            tab_task = fetch_invidious(f"/channels/{ucid}/playlists", force_instance=force_instance)
        elif tab == "community":
            tab_task = fetch_invidious(f"/channels/{ucid}/community", force_instance=force_instance)

        tab_data = await tab_task if tab_task else {}

        final_videos = tab_data.get("videos", tab_data) if isinstance(tab_data, (dict, list)) and tab == "videos" else []
        final_shorts = tab_data.get("videos", tab_data) if isinstance(tab_data, (dict, list)) and tab == "shorts" else []
        
        playlists = []
        if tab == "playlists":
            raw_pl = tab_data.get("playlists", []) if isinstance(tab_data, dict) else (tab_data if isinstance(tab_data, list) else [])
            for pl in raw_pl:
                thumb = pl.get("playlistThumbnail", "")
                if thumb and not thumb.startswith("http"):
                    thumb = f"https://img.youtube.com/vi/{thumb}/mqdefault.jpg"
                playlists.append({
                    "id": pl.get("playlistId", ""),
                    "title": pl.get("title", ""),
                    "video_count": pl.get("videoCount", 0),
                    "thumbnail": thumb,
                })

        author_name = channel_data.get("author")
        author_icon = channel_data.get("authorThumbnails", [{"url": ""}])[-1]["url"] if channel_data.get("authorThumbnails") else ""

        community = []
        if tab == "community":
            raw_com = tab_data.get("comments", []) if isinstance(tab_data, dict) else (tab_data if isinstance(tab_data, list) else [])
            community = [{
                "id": post.get("commentId", ""),
                "content": post.get("contentHtml", "").replace("\n", "<br>"),
                "published_text": post.get("publishedText", ""),
                "likes": post.get("likeCount", 0),
                "author": author_name,
                "author_icon": author_icon,
            } for post in raw_com]

        return templates.TemplateResponse("channel.html", {
            "request": request,
            "ucid": ucid,
            "author": author_name,
            "author_icon": author_icon,
            "sub_count": channel_data.get("subCountText", "非公開"),
            "description": channel_data.get("descriptionHtml", ""),
            "videos": final_videos if isinstance(final_videos, list) else [],
            "shorts": final_shorts if isinstance(final_shorts, list) else [],
            "playlists": playlists,
            "community": community,
            "sort_by": sort_by,
            "tab": tab
        })
    except httpx.TimeoutException:
        return templates.TemplateResponse("apitimeout.html", {"request": request})
    except Exception:
        return templates.TemplateResponse("apiallerror.html", {"request": request, "instances": INVIDIOUS_INSTANCES})

@router.get("/playlist", response_class=HTMLResponse)
async def playlist(request: Request, list: str = Query(...), force_instance: str = Query(None)):
    try:
        data = await fetch_invidious(f"/playlists/{list}", force_instance=force_instance)
        return templates.TemplateResponse("playlist.html", {
            "request": request,
            "title": data.get("title"),
            "playlistId": list,
            "author": data.get("author"),
            "authorId": data.get("authorId"),
            "videos": data.get("videos", []),
            "description": data.get("descriptionHtml", "")
        })
    except httpx.TimeoutException:
        return templates.TemplateResponse("apitimeout.html", {"request": request})
    except Exception:
        return templates.TemplateResponse("apiallerror.html", {"request": request, "instances": INVIDIOUS_INSTANCES})
