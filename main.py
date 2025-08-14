# main.py
import uvicorn
from fastapi import FastAPI
from api.endpoints import router as api_router

app = FastAPI(
    title="Anime Parser API",
    description="API для управления скрапингом данных об аниме с jut.su и Jikan.",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1", tags=["Scraping"])

@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в Anime Parser API! Документация доступна по адресу /docs"}

if __name__ == "__main__":
    # Установка Playwright браузеров (нужно выполнить один раз)
    # import os
    # os.system('playwright install')
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

