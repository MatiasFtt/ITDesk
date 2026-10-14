from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pwdlib import PasswordHash
from sqlalchemy import select, text

from app.database import Base, SessionLocal, engine
from app.models.usuario import Usuario
from app.routers.auth import router as auth_router
from app.routers.departamentos import router as departamentos_router
from app.routers.tickets import router as tickets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    # Actualiza la restricción de estado en bases PostgreSQL ya existentes.
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            definition = connection.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = 'tickets'::regclass "
                "AND conname = 'tickets_estado_check'"
            )).scalar_one_or_none()
            if definition and "SOLUCIONANDO" not in definition:
                connection.execute(text(
                    "ALTER TABLE tickets DROP CONSTRAINT tickets_estado_check"
                ))
                connection.execute(text(
                    "ALTER TABLE tickets ADD CONSTRAINT tickets_estado_check "
                    "CHECK (estado IN ('ABIERTO', 'EN_PROCESO', "
                    "'ESPERANDO_USUARIO', 'SOLUCIONANDO', 'RESUELTO', 'CERRADO'))"
                ))

    admin_email = os.getenv("ITDESK_ADMIN_EMAIL", "admin@itdesk.local").strip().lower()
    admin_password = os.getenv("ITDESK_ADMIN_PASSWORD")
    if admin_password:
        with SessionLocal() as db:
            admin = db.scalar(select(Usuario).where(Usuario.email == admin_email))
            password_hash = PasswordHash.recommended().hash(admin_password)
            if admin is None:
                admin = Usuario(
                    nombre="Administrador",
                    email=admin_email,
                    password_hash=password_hash,
                    rol="ADMIN",
                    activo=True,
                )
                db.add(admin)
            else:
                admin.nombre = "Administrador"
                admin.password_hash = password_hash
                admin.rol = "ADMIN"
                admin.activo = True
            db.commit()
    yield


app = FastAPI(
    title="ITDesk",
    description="Sistema de gestión de soporte técnico",
    version="1.0.0",
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(departamentos_router)
app.include_router(auth_router)
app.include_router(tickets_router)


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(TEMPLATES_DIR / "login.html")


@app.get("/login", include_in_schema=False)
def pagina_login():
    return FileResponse(TEMPLATES_DIR / "login.html")


@app.get("/registro", include_in_schema=False)
def pagina_registro():
    return FileResponse(TEMPLATES_DIR / "registro.html")


@app.get("/dashboard", include_in_schema=False)
def pagina_dashboard():
    return FileResponse(TEMPLATES_DIR / "dashboard.html")


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "error", "database": "disconnected"}
