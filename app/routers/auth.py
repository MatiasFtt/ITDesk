
import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import (
    UsuarioRegistro,
    UsuarioLogin,
    UsuarioRespuesta,
    TokenRespuesta,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if not JWT_SECRET_KEY:
    raise RuntimeError("Falta configurar JWT_SECRET_KEY en .env")


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def crear_token(usuario: Usuario) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@router.post(
    "/registro",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(
    datos: UsuarioRegistro,
    db: Session = Depends(get_db),
):
    email = normalizar_email(datos.email)

    existente = db.scalar(
        select(Usuario).where(Usuario.email == email)
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo",
        )

    usuario = Usuario(
        nombre=datos.nombre.strip(),
        email=email,
        password_hash=password_hash.hash(datos.password),
        rol="USUARIO",
        activo=True,
    )

    db.add(usuario)

    try:
        db.commit()
        db.refresh(usuario)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar el usuario",
        )

    return usuario


@router.post("/login", response_model=TokenRespuesta)
def iniciar_sesion(
    datos: UsuarioLogin,
    db: Session = Depends(get_db),
):
    email = normalizar_email(datos.email)

    usuario = db.scalar(
        select(Usuario).where(Usuario.email == email)
    )

    if (
        usuario is None
        or not password_hash.verify(
            datos.password, usuario.password_hash
        )
        or not usuario.activo
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos, o cuenta inactiva",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": crear_token(usuario),
        "token_type": "bearer",
    }


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    token = credenciales.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        usuario_id = payload.get("sub")

        if not usuario_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )

        usuario_id = int(usuario_id)

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o vencido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.get(Usuario, usuario_id)

    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo",
        )

    return usuario


@router.get("/me", response_model=UsuarioRespuesta)
def consultar_usuario_actual(
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    return usuario
