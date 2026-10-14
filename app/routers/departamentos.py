
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Departamento
from app.schemas.departamento import (
    DepartamentoCrear,
    DepartamentoRespuesta,
)

router = APIRouter(
    prefix="/api/departamentos",
    tags=["Departamentos"],
)


@router.get("/", response_model=list[DepartamentoRespuesta])
def listar_departamentos(db: Session = Depends(get_db)):
    consulta = (
        select(Departamento)
        .where(Departamento.activo.is_(True))
        .order_by(Departamento.nombre)
    )
    return db.scalars(consulta).all()


@router.get(
    "/{departamento_id}",
    response_model=DepartamentoRespuesta,
)
def obtener_departamento(
    departamento_id: int,
    db: Session = Depends(get_db),
):
    departamento = db.get(Departamento, departamento_id)

    if departamento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Departamento no encontrado",
        )

    return departamento


@router.post(
    "/",
    response_model=DepartamentoRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_departamento(
    datos: DepartamentoCrear,
    db: Session = Depends(get_db),
):
    departamento = Departamento(
        nombre=datos.nombre.strip(),
        descripcion=datos.descripcion,
    )

    db.add(departamento)

    try:
        db.commit()
        db.refresh(departamento)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un departamento con ese nombre",
        )

    return departamento
