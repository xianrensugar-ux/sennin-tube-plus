import httpx

# --- 各種 API インスタンス一覧 ---
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

COBALT_INSTANCES = [
    "https://co.wuk.sh",
    "https://api.cobalt.tools",
    "https://cobalt.qewertyy.dev"
]

# --- 超高速コネクションプール設定 ---
limits = httpx.Limits(max_connections=500, max_keepalive_connections=200, keepalive_expiry=30.0)
timeout = httpx.Timeout(4.0, connect=1.5)

# コネクション再利用の最適化
client_session = httpx.AsyncClient(
    timeout=timeout,
    limits=limits,
    follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
)
