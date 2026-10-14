
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    __table_args__ = (
        CheckConstraint(
            "rol IN ('ADMIN', 'TECNICO', 'USUARIO')",
            name="usuarios_rol_check",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(
        String(20), nullable=False, default="USUARIO"
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tickets_creados: Mapped[list["Ticket"]] = relationship(
        back_populates="usuario",
        foreign_keys="Ticket.usuario_id",
    )

    tickets_asignados: Mapped[list["Ticket"]] = relationship(
        back_populates="tecnico",
        foreign_keys="Ticket.tecnico_id",
    )

    comentarios: Mapped[list["Comentario"]] = relationship(
        back_populates="usuario"
    )

    cambios_historial: Mapped[list["HistorialTicket"]] = relationship(
        back_populates="usuario"
    )
