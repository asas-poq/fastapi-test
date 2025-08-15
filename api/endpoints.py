# api/endpoints.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from core.scraping_manager import ScrapingManager

router = APIRouter()
manager = ScrapingManager()

class AnimeRequest(BaseModel):
    anime_slug: str

@router.post("/scrape/specific", status_code=202)
async def scrape_specific_anime(request: AnimeRequest, background_tasks: BackgroundTasks):
    """
    Эндпоинт для добавления одного конкретного аниме по его slug.
    Запускается в фоновом режиме.
    """
    background_tasks.add_task(manager.add_specific_anime, request.anime_slug)
    return {"message": f"Процесс добавления аниме '{request.anime_slug}' запущен в фоновом режиме."}

@router.post("/scrape/bulk/{limit}", status_code=202)
async def scrape_bulk_anime(limit: int, background_tasks: BackgroundTasks):
    """
    Эндпоинт для массового добавления аниме.
    `limit` - максимальное количество новых аниме для добавления.
    """
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Лимит должен быть больше нуля.")
    background_tasks.add_task(manager.add_bulk_anime, limit)
    return {"message": f"Процесс добавления {limit} новых аниме запущен в фоновом режиме."}

# Глобальная переменная для отслеживания состояния задачи
continuous_task_running = False

@router.post("/scrape/continuous/start", status_code=200)
async def start_continuous_scraping(background_tasks: BackgroundTasks):
    """
    Запускает бесконечный процесс скрапинга.
    """
    global continuous_task_running
    if continuous_task_running:
        raise HTTPException(status_code=409, detail="Непрерывный скрапинг уже запущен.")
    
    continuous_task_running = True
    background_tasks.add_task(manager.run_continuous_scraping)
    return {"message": "Непрерывный скрапинг успешно запущен."}

# Этот эндпоинт в реальности не остановит фоновую задачу,
# он просто сбросит флаг. Для реальной остановки нужны более сложные механизмы (например, Celery).
@router.post("/scrape/continuous/stop", status_code=200)
async def stop_continuous_scraping():
    """
    Останавливает запуск новых циклов непрерывного скрапинга.
    (Текущий цикл завершится).
    """
    global continuous_task_running
    if not continuous_task_running:
        raise HTTPException(status_code=409, detail="Непрерывный скрапинг не был запущен.")
    
    continuous_task_running = False # Предотвратит запуск новых циклов в логике run_continuous_scraping
    return {"message": "Отправлен сигнал остановки. Текущий цикл будет завершен."}











# api/endpoints.py
import sqlite3
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError


db_url = "sqlite:///./test.db"
db_path = "./test.db"  # для sqlite3 нужен путь без 'sqlite:///'

@router.get("/db/tables")
async def list_tables():
    """
    Показывает список таблиц в БД.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db/table/{table_name}")
async def get_table_data(table_name: str):
    """
    Показывает содержимое указанной таблицы.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # чтобы получать dict вместо tuple
        cursor = conn.cursor()

        # Проверим, существует ли таблица
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
        if cursor.fetchone() is None:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Таблица '{table_name}' не найдена.")

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        conn.close()

        return JSONResponse(content={"table": table_name, "rows": [dict(row) for row in rows]})
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка SQL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

