import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Comentario, Departamento, HistorialTicket, Ticket
from app.models.usuario import Usuario
from app.routers.auth import obtener_usuario_actual
from app.schemas.ticket import (
    ComentarioCrear,
    EstadoActualizar,
    TicketCrear,
    TicketRespuesta,
)

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])
logger = logging.getLogger(__name__)
ESTADOS = {"ABIERTO", "EN_PROCESO", "ESPERANDO_USUARIO", "SOLUCIONANDO", "RESUELTO", "CERRADO"}
PRIORIDADES = {"BAJA", "MEDIA", "ALTA", "CRITICA"}


def cargar_ticket(db: Session, ticket_id: int) -> Ticket:
    consulta = (
        select(Ticket)
        .options(
            selectinload(Ticket.usuario),
            selectinload(Ticket.departamento),
            selectinload(Ticket.comentarios).selectinload(Comentario.usuario),
            selectinload(Ticket.historial).selectinload(HistorialTicket.usuario),
        )
        .where(Ticket.id == ticket_id)
    )
    ticket = db.scalar(consulta)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


def cargar_ticket_resumen(db: Session, ticket_id: int) -> Ticket:
    consulta = (
        select(Ticket)
        .options(
            selectinload(Ticket.usuario),
            selectinload(Ticket.departamento),
        )
        .where(Ticket.id == ticket_id)
    )
    ticket = db.scalar(consulta)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


def serializar(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "codigo": ticket.codigo,
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "prioridad": ticket.prioridad,
        "estado": ticket.estado,
        "usuario_id": ticket.usuario_id,
        "nombre_usuario": ticket.usuario.nombre,
        "tecnico_id": ticket.tecnico_id,
        "departamento_id": ticket.departamento_id,
        "departamento": ticket.departamento.nombre,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
        "comentarios": [
            {"id": c.id, "comentario": c.comentario, "usuario_id": c.usuario_id,
             "nombre_usuario": c.usuario.nombre, "created_at": c.created_at}
            for c in sorted(ticket.comentarios, key=lambda item: item.created_at)
        ],
        "historial": [
            {"id": h.id, "accion": h.accion, "estado_anterior": h.estado_anterior,
             "estado_nuevo": h.estado_nuevo, "detalle": h.detalle,
             "usuario_id": h.usuario_id, "nombre_usuario": h.usuario.nombre,
             "created_at": h.created_at}
            for h in sorted(ticket.historial, key=lambda item: item.created_at)
        ],
    }


def serializar_resumen(ticket: Ticket) -> dict:
    """Payload ligero para la lista del panel; no carga comentarios."""
    return {
        "id": ticket.id,
        "codigo": ticket.codigo,
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "prioridad": ticket.prioridad,
        "estado": ticket.estado,
        "usuario_id": ticket.usuario_id,
        "nombre_usuario": ticket.usuario.nombre,
        "tecnico_id": ticket.tecnico_id,
        "departamento_id": ticket.departamento_id,
        "departamento": ticket.departamento.nombre,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
    }


@router.get("/", response_model=list[TicketRespuesta])
def listar_tickets(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    consulta = select(Ticket).options(
        selectinload(Ticket.usuario),
        selectinload(Ticket.departamento),
    )
    if usuario.rol == "USUARIO":
        consulta = consulta.where(Ticket.usuario_id == usuario.id)
    consulta = consulta.order_by(Ticket.created_at.desc())
    return [serializar_resumen(t) for t in db.scalars(consulta).all()]


@router.post("/", response_model=TicketRespuesta, status_code=status.HTTP_201_CREATED)
def crear_ticket(
    datos: TicketCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    if usuario.rol == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El perfil administrador no puede crear tickets",
        )
    prioridad = datos.prioridad.strip().upper()
    if prioridad not in PRIORIDADES:
        raise HTTPException(status_code=422, detail="Prioridad no válida")
    departamento = db.scalar(select(Departamento).where(
        Departamento.id == datos.departamento_id, Departamento.activo.is_(True)
    ))
    if departamento is None:
        raise HTTPException(status_code=422, detail="Departamento no disponible")
    try:
        ticket = Ticket(
            # La columna codigo admite 20 caracteres; este valor solo vive
            # durante el INSERT previo a asignar el código definitivo.
            codigo=f"T-{uuid4().hex[:18]}", titulo=datos.titulo.strip(),
            descripcion=datos.descripcion.strip(), prioridad=prioridad,
            estado="ABIERTO", usuario_id=usuario.id,
            departamento_id=departamento.id,
        )
        db.add(ticket)
        db.flush()
        ticket.codigo = f"ITD-{ticket.id:06d}"
        db.add(HistorialTicket(ticket_id=ticket.id, usuario_id=usuario.id,
                               accion="Ticket creado", estado_nuevo="ABIERTO"))
        db.commit()
        return serializar(cargar_ticket(db, ticket.id))
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "Falló la transacción al crear un ticket (usuario_id=%s, departamento_id=%s)",
            usuario.id,
            datos.departamento_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el ticket. Consulta los registros del servidor.",
        )


@router.get("/{ticket_id}", response_model=TicketRespuesta)
def obtener_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    ticket = cargar_ticket(db, ticket_id)
    if usuario.rol == "USUARIO" and ticket.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return serializar(ticket)


@router.post("/{ticket_id}/comentarios", response_model=TicketRespuesta)
def agregar_comentario(
    ticket_id: int,
    datos: ComentarioCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    ticket = cargar_ticket(db, ticket_id)
    if usuario.rol == "USUARIO" and ticket.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.estado in {"RESUELTO", "CERRADO"}:
        raise HTTPException(status_code=409, detail="No se puede modificar un ticket finalizado")
    db.add(Comentario(ticket_id=ticket.id, usuario_id=usuario.id,
                      comentario=datos.comentario.strip()))
    db.add(HistorialTicket(ticket_id=ticket.id, usuario_id=usuario.id,
                           accion="Comentario agregado"))
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    return serializar(cargar_ticket(db, ticket.id))


@router.patch("/{ticket_id}/estado", response_model=TicketRespuesta)
def actualizar_estado(
    ticket_id: int,
    datos: EstadoActualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    ticket = cargar_ticket(db, ticket_id)
    if usuario.rol == "USUARIO" or (usuario.rol == "TECNICO" and ticket.tecnico_id not in (None, usuario.id)):
        raise HTTPException(status_code=403, detail="No tienes permiso para cambiar este estado")
    estado = datos.estado.strip().upper()
    if estado not in ESTADOS:
        raise HTTPException(status_code=422, detail="Estado no válido")
    anterior = ticket.estado
    if anterior in {"RESUELTO", "CERRADO"}:
        raise HTTPException(status_code=409, detail="Un ticket finalizado no puede modificarse")
    ticket.estado = estado
    ticket.updated_at = datetime.now(timezone.utc)
    if estado == "RESUELTO":
        ticket.resolved_at = ticket.updated_at
    if estado == "CERRADO":
        ticket.closed_at = ticket.updated_at
    if usuario.rol == "TECNICO" and ticket.tecnico_id is None:
        ticket.tecnico_id = usuario.id
    db.add(HistorialTicket(ticket_id=ticket.id, usuario_id=usuario.id,
                           accion="Estado actualizado", estado_anterior=anterior,
                           estado_nuevo=estado))
    db.commit()
    return serializar_resumen(cargar_ticket_resumen(db, ticket.id))
