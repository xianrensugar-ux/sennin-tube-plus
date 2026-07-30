import httpx

INVIDIOUS_INSTANCES = [
    "https://invidious.ritoge.com",
    "https://yt.omada.cafe",
    "https://invidious.darkness.services",
    "https://invidious.f5.si",
    "https://invidious.ducks.party",
    "https://y.com.sb",
    "https://super8.absturztau.be",
    "https://inv.zoomerville.com",
    "https://invidious.nerdvpn.de",
    "https://inv.thepixora.com"
]

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://piped-api.garudalinux.org",
    "https://api.piped.privacydev.net",
    "https://pipedapi.lunar.icu"
]

limits = httpx.Limits(max_connections=400, max_keepalive_connections=150)
timeout = httpx.Timeout(5.0, connect=2.0)
client_session = httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True)
