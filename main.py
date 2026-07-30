from fastapi import FastAPI
from routes import video, channel, history, pages

app = FastAPI()

app.include_router(pages.router)
app.include_router(video.router)
app.include_router(channel.router)
app.include_router(history.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
