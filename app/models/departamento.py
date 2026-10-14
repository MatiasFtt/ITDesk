
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Identity,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Departamento(Base):
    __tablename__ = "departamentos"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )

    nombre: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(Text)

    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="departamento"
    )
