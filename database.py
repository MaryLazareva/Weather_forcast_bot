import os
from dotenv import load_dotenv

from contextlib import asynccontextmanager
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

load_dotenv()


engine = create_async_engine(os.getenv('DATABASE_URL')) # создание объекта "движка" для подключения к базе данных и выполнения SQL-запросов через SQLAlchemy
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False) # создание фабрики сессий для выполнения операций с базой данных 
Base = declarative_base()  # создание базового класса, от которого будут наследоваться все модели базы данных

@asynccontextmanager
async def get_db():
    """Подключение к базе данных"""
    async with SessionLocal() as session:  # Асинхронный контекстный менеджер используется для корректного открытия и закрытия сессии
        yield session
 
