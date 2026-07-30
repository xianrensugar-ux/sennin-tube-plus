import asyncio
import random
from typing import Any, Dict, List
import httpx

from config import INVIDIOUS_INSTANCES, PIPED_INSTANCES, COBALT_INSTANCES, client_session
from utils.cache import video_cache, search_cache

async def race_requests(urls: List[str], params: dict = None) -> Any:
    """複数インスタンスへ同時に投機的リクエストを送り、最初に成功した結果を返す"""
    tasks = [
        asyncio.create_task(client_session.get(url, params=params))
        for url in urls
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    # 未完了のタスクはすべて即時キャンセルしてネットワークリソースを解放
    for t in pending:
        t.cancel()

    for t in done:
        try:
            resp = t.result()
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    raise Exception("All raced API requests failed")

async def fetch_invidious(endpoint: str, params: dict = None, force_instance: str = None) -> Any:
    if force_instance:
        url = f"{force_instance.rstrip('/')}/api/v1{endpoint}"
        resp = await client_session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    instances = list(INVIDIOUS_INSTANCES)
    random.shuffle(instances)
    urls = [f"{inst.rstrip('/')}/api/v1{endpoint}" for inst in instances[:4]]
    
    try:
        return await race_requests(urls, params=params)
    except Exception:
        # レース取得失敗時の順次フォールバック
        for inst in instances[4:]:
            try:
                url = f"{inst.rstrip('/')}/api/v1{endpoint}"
                resp = await client_session.get(url, params=params)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                continue
    raise Exception("Invidious endpoints completely unavailable")

async def fetch_cobalt_stream(v: str) -> Optional[Dict[str, Any]]:
    """Cobalt API を使用したストリームURL・ダウンロード元データの高速取得"""
    yt_url = f"https://www.youtube.com/watch?v={v}"
    instances = list(COBALT_INSTANCES)
    random.shuffle(instances)

    for inst in instances:
        try:
            resp = await client_session.post(
                f"{inst.rstrip('/')}/api/json",
                json={"url": yt_url, "vQuality": "max", "isAudioOnly": False},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=3.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") in ["stream", "redirect", "success"]:
                    return data
        except Exception:
            continue
    return None

async def fetch_piped_stream(v: str) -> Dict[str, Any]:
    """Piped API からのフォールバック取得と Invidious 互換整形"""
    instances = list(PIPED_INSTANCES)
    random.shuffle(instances)
    urls = [f"{inst.rstrip('/')}/streams/{v}" for inst in instances[:3]]
    piped_data = await race_requests(urls)

    return {
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

async def fetch_video_ultra(v: str, force_instance: str = None) -> dict:
    """キャッシュ ➔ Invidious ➔ Piped ➔ Cobalt のマルチレイヤー高速取得"""
    cache_key = f"video:{v}"
    cached = await video_cache.get(cache_key)
    if cached:
        return cached

    # 第1優先: Invidious
    try:
        data = await fetch_invidious(f"/videos/{v}", force_instance=force_instance)
        await video_cache.set(cache_key, data)
        return data
    except Exception:
        pass

    # 第2優先: Piped
    try:
        data = await fetch_piped_stream(v)
        await video_cache.set(cache_key, data)
        return data
    except Exception:
        pass

    # 第3優先: Cobalt API
    cobalt_data = await fetch_cobalt_stream(v)
    if cobalt_data:
        stream_url = cobalt_data.get("url")
        data = {
            "title": f"Video ({v})",
            "author": "Unknown",
            "authorId": "",
            "authorThumbnails": [],
            "subCountText": "",
            "viewCount": 0,
            "likeCount": 0,
            "descriptionHtml": "Loaded via Cobalt Fallback Engine.",
            "formatStreams": [{"url": stream_url, "qualityLabel": "Auto"}],
            "adaptiveFormats": [],
            "recommendedVideos": []
        }
        await video_cache.set(cache_key, data)
        return data

    raise Exception("All Video API endpoints failed to resolve stream")
