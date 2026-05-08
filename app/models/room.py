import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, GUID


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = {"extend_existing": True}

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    hotel_id = Column(GUID, ForeignKey("hotels.id"), nullable=False)
    tipo = Column(String(100), nullable=False)
    categoria = Column(String(100))
    capacidad_maxima = Column(Integer, nullable=False)
    descripcion = Column(Text)
    imagenes = Column(JSON, default=list)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    hotel = relationship("Hotel", back_populates="rooms")
    availability = relationship("Availability", back_populates="room")
    tariffs = relationship("Tariff", back_populates="room")
