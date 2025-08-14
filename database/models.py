# database/models.py
from sqlalchemy import (create_engine, Column, Integer, String, Text, DECIMAL,
                        ForeignKey, Table, TIMESTAMP, func)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Связующая таблица для anime и genres
anime_genres_table = Table('anime_genres', Base.metadata,
    Column('anime_id', Integer, ForeignKey('anime.id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id'), primary_key=True)
)

class ContentType(Base):
    __tablename__ = 'content_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

class Anime(Base):
    __tablename__ = 'anime'
    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(255), unique=True, nullable=False)
    title_rus = Column(String(255), nullable=False)
    title_orig = Column(String(255))
    description_api = Column(Text)
    poster_url_api = Column(String(512))
    age_rating = Column(String(100))
    status = Column(String(100))
    year = Column(Integer)
    score = Column(DECIMAL(4, 2))
    content_type_id = Column(Integer, ForeignKey('content_types.id'))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    content_type = relationship("ContentType")
    seasons = relationship("Season", back_populates="anime", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="anime", cascade="all, delete-orphan")
    genres = relationship("Genre", secondary=anime_genres_table, back_populates="animes")

class Season(Base):
    __tablename__ = 'seasons'
    id = Column(Integer, primary_key=True, autoincrement=True)
    anime_id = Column(Integer, ForeignKey('anime.id'), nullable=False)
    season_number = Column(Integer, nullable=False)
    title = Column(String(255))
    
    anime = relationship("Anime", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season", cascade="all, delete-orphan")

class Episode(Base):
    __tablename__ = 'episodes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    anime_id = Column(Integer, ForeignKey('anime.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('seasons.id'))
    episode_number = Column(Integer, nullable=False)
    title = Column(String(255))
    source_url = Column(String(512), unique=True, nullable=False)
    poster_local_path = Column(String(512))
    duration_sec = Column(Integer)
    opening_start_sec = Column(Integer)
    opening_end_sec = Column(Integer)
    ending_start_sec = Column(Integer)
    ending_end_sec = Column(Integer)
    next_episode_url = Column(String(512))
    created_at = Column(TIMESTAMP, server_default=func.now())

    anime = relationship("Anime", back_populates="episodes")
    season = relationship("Season", back_populates="episodes")

class Genre(Base):
    __tablename__ = 'genres'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    
    animes = relationship("Anime", secondary=anime_genres_table, back_populates="genres")

