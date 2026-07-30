import random
from typing import Any
from config import INVIDIOUS_INSTANCES, PIPED_INSTANCES, client_session
from utils.cache import video_cache

async def fetch_invidious(endpoint: str, params: dict = None, force_instance: str = None) -> Any:
    if force_instance:
        instances = [force_instance]
    else:
        instances = list(INVIDIOUS_INSTANCES)
        random.shuffle(instances)

    last_error = None
    for instance in instances[:5]:
        try:
            url = f"{instance.rstrip('/')}/api/v1{endpoint}"
            response = await client_session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_error = e
            continue

    raise last_error if last_error else Exception("All Invidious instances failed")

async def fetch_piped(endpoint: str, params: dict = None) -> Any:
    instances = list(PIPED_INSTANCES)
    random.shuffle(instances)
    
    for instance in instances:
        try:
            url = f"{instance.rstrip('/')}{endpoint}"
            response = await client_session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            continue
    raise Exception("All Piped instances failed")

async def fetch_video_smart(v: str, force_instance: str = None) -> dict:
    cache_key = f"video:{v}"
    cached = video_cache.get(cache_key)
    if cached:
        return cached

    try:
        data = await fetch_invidious(f"/videos/{v}", force_instance=force_instance)
        video_cache.set(cache_key, data)
        return data
    except Exception:
        piped_data = await fetch_piped(f"/streams/{v}")
        
        formatted_data = {
            "title": piped_data.get("title"),
            "author": piped_data.get("uploader"),
            "authorId": piped_data.get("uploaderUrl", "").replace("/channel/", ""),
            "authorThumbnails": [{"url": piped_data.get("uploaderAvatar")}],
            "subCountText": f"{piped_data.get('uploaderSubscriberCount', 0)} subscribers",
            "viewCount": piped_data.get("views", 0),
            "likeCount": piped_data.get("likes", 0),
            "descriptionHtml": piped_data.get("description", ""),
            "formatStreams": [
                {"url": s.get("url"), "qualityLabel": s.get("quality")}
                for s in piped_data.get("videoStreams", []) if s.get("url")
            ],
            "adaptiveFormats": [
                {"url": s.get("url"), "type": s.get("mimeType", ""), "qualityLabel": s.get("quality")}
                for s in piped_data.get("audioStreams", []) + piped_data.get("videoStreams", []) if s.get("url")
            ],
            "recommendedVideos": [
                {
                    "videoId": r.get("url", "").replace("/watch?v=", ""),
                    "title": r.get("title"),
                    "author": r.get("uploaderName"),
                    "viewCountText": f"{r.get('views', 0)} views"
                } for r in piped_data.get("relatedStreams", [])
            ]
        }
        video_cache.set(cache_key, formatted_data)
        return formatted_data
