from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCrear(BaseModel):
    titulo: str = Field(min_length=4, max_length=200)
    descripcion: str = Field(min_length=10, max_length=10000)
    prioridad: str = "MEDIA"
    departamento_id: int


class ComentarioCrear(BaseModel):
    comentario: str = Field(min_length=1, max_length=5000)


class EstadoActualizar(BaseModel):
    estado: str


class ComentarioRespuesta(BaseModel):
    id: int
    comentario: str
    usuario_id: int
    nombre_usuario: str
    created_at: datetime


class HistorialRespuesta(BaseModel):
    id: int
    accion: str
    estado_anterior: str | None
    estado_nuevo: str | None
    detalle: str | None
    usuario_id: int
    nombre_usuario: str
    created_at: datetime


class TicketRespuesta(BaseModel):
    id: int
    codigo: str
    titulo: str
    descripcion: str
    prioridad: str
    estado: str
    usuario_id: int
    nombre_usuario: str
    tecnico_id: int | None
    departamento_id: int
    departamento: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    comentarios: list[ComentarioRespuesta] = Field(default_factory=list)
    historial: list[HistorialRespuesta] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
