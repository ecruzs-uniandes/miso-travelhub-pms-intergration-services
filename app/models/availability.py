import uuid
from sqlalchemy import Column, Integer, DateTime, Date, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, GUID


class Availability(Base):
    __tablename__ = "availability"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    room_id = Column(GUID, ForeignKey("rooms.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    unidades_disponibles = Column(Integer, nullable=False, default=0)
    unidades_reservadas = Column(Integer, nullable=False, default=0)
    ultima_actualizacion = Column(DateTime, default=func.now())
    fuente_actualizacion = Column(String(50))

    room = relationship("Room", back_populates="availability")

    __table_args__ = (
        UniqueConstraint("room_id", "fecha", name="uq_room_date"),
        {"extend_existing": True},
    )
