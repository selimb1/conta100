
import os, json
from sqlalchemy import create_engine, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./data/conta.db")
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Client(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    cuit: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    condicion_fiscal: Mapped[str] = mapped_column(String(50))
    fecha_alta: Mapped[str] = mapped_column(String(30), default="")

class Document(Base):
    __tablename__ = "documentos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, index=True)
    tipo: Mapped[str] = mapped_column(String(100))
    path: Mapped[str] = mapped_column(Text)
    fecha_carga: Mapped[str] = mapped_column(String(30), default="")

class Result(Base):
    __tablename__ = "resultados"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, index=True)
    tipo: Mapped[str] = mapped_column(String(50))
    contenido_json: Mapped[dict] = mapped_column(JSON)
    fecha_generacion: Mapped[str] = mapped_column(String(30), default="")

class Normativa(Base):
    __tablename__ = "normativas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(50), unique=True)
    version: Mapped[str] = mapped_column(String(50))
    contenido_json: Mapped[dict] = mapped_column(JSON)

def init_db():
    os.makedirs("./data", exist_ok=True)
    Base.metadata.create_all(engine)
