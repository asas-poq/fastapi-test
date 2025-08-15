# database/db_manager.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import config
from .models import Base, Anime, Season, Episode, Genre, ContentType

from sqlalchemy.exc import OperationalError, SQLAlchemyError

class DatabaseManager:
    def __init__(self):
        try:
            # Пытаемся подключиться к MySQL
            db_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}"
            self.engine = create_engine(db_url, echo=False)
            
            # Проверка соединения
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            
            print("✅ Подключено к MySQL")

        except (OperationalError, SQLAlchemyError, Exception) as e:
            # Любая ошибка подключения — переключаемся на SQLite
            print(f"⚠️ MySQL недоступен ({e}), переключаюсь на SQLite")
            db_url = "sqlite:///./test.db"
            self.engine = create_engine(db_url, echo=False)

        # Создаем таблицы
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)


    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_or_create(self, session, model, defaults=None, **kwargs):
        """
        Получает объект из БД или создает новый, если он не найден.
        """
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            params = {**kwargs, **(defaults or {})}
            instance = model(**params)
            session.add(instance)
            return instance, True

    def get_all_anime_slugs(self):
        """Возвращает список всех slug'ов аниме в базе."""
        with self.session_scope() as session:
            slugs = session.query(Anime.slug).all()
            return [slug[0] for slug in slugs]

    def anime_exists(self, slug):
        """Проверяет, существует ли аниме с данным slug."""
        with self.session_scope() as session:
            return session.query(Anime).filter_by(slug=slug).count() > 0

# Синглтон экземпляр
db_manager = DatabaseManager()
















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
