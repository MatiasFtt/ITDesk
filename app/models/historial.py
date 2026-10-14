
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HistorialTicket(Base):
    __tablename__ = "historial_tickets"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    accion: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    estado_anterior: Mapped[str | None] = mapped_column(String(30))
    estado_nuevo: Mapped[str | None] = mapped_column(String(30))
    detalle: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    ticket: Mapped["Ticket"] = relationship(
        back_populates="historial"
    )
    usuario: Mapped["Usuario"] = relationship(
        back_populates="cambios_historial"
    )
