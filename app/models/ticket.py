
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    __table_args__ = (
        CheckConstraint(
            "prioridad IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')",
            name="tickets_prioridad_check",
        ),
        CheckConstraint(
            "estado IN ('ABIERTO', 'EN_PROCESO', "
            "'ESPERANDO_USUARIO', 'SOLUCIONANDO', 'RESUELTO', 'CERRADO')",
            name="tickets_estado_check",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    codigo: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    prioridad: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MEDIA"
    )
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ABIERTO"
    )

    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=False
    )
    tecnico_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=True
    )
    departamento_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departamentos.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    usuario: Mapped["Usuario"] = relationship(
        back_populates="tickets_creados",
        foreign_keys=[usuario_id],
    )
    tecnico: Mapped["Usuario | None"] = relationship(
        back_populates="tickets_asignados",
        foreign_keys=[tecnico_id],
    )
    departamento: Mapped["Departamento"] = relationship(
        back_populates="tickets"
    )
    comentarios: Mapped[list["Comentario"]] = relationship(
        back_populates="ticket",
        passive_deletes=True,
    )
    historial: Mapped[list["HistorialTicket"]] = relationship(
        back_populates="ticket",
        passive_deletes=True,
    )
