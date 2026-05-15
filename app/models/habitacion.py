"""Habitacion — referencia al modelo canónico del proyecto.

pms-integration NO crea habitaciones — solo las usa como FK target en disponibilidad.
El modelo mapea las 11 columnas NOT NULL canónicas.
"""
from sqlalchemy import Column, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Habitacion(Base):
    __tablename__ = "habitacion"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    hotelId = Column("hotelId", String, ForeignKey("hotel.id"), nullable=False)
    tipo = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    capacidadMaxima = Column("capacidadMaxima", Integer, nullable=False)
    descripcion = Column(String, nullable=False)
    imagenes = Column(JSON, nullable=False)
    tipo_habitacion = Column(String, nullable=False)
    tipo_cama = Column(JSON, nullable=False)
    tamano_habitacion = Column(String, nullable=False)
    amenidades = Column(JSON, nullable=False)

    hotel = relationship("Hotel", back_populates="habitaciones")
    disponibilidades = relationship("Disponibilidad", back_populates="habitacion")
