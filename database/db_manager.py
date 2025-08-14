# database/db_manager.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import config
from .models import Base, Anime, Season, Episode, Genre, ContentType

class DatabaseManager:
    def __init__(self):
        db_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}"
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine) # Создает таблицы, если их нет
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

