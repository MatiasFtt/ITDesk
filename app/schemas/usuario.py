
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsuarioRegistro(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class UsuarioLogin(BaseModel):
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=1, max_length=128)


class UsuarioRespuesta(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str
    activo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str = "bearer"
