import uuid
from sqlalchemy import Column, String, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Tariff(Base):
    __tablename__ = "tariffs"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    precio_base = Column(Numeric(12, 2), nullable=False)
    moneda = Column(String(3), nullable=False, default="USD")
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    descuento = Column(Numeric(5, 2), default=0)
    created_at = Column(DateTime, default=func.now())

    room = relationship("Room", back_populates="tariffs")
