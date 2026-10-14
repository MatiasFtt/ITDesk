
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartamentoBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = None


class DepartamentoCrear(DepartamentoBase):
    pass


class DepartamentoRespuesta(DepartamentoBase):
    id: int
    activo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
ññ