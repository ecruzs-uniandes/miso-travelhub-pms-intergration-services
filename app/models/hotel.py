"""Hotel — referencia al modelo canónico del proyecto.

pms-integration NO crea hoteles. Solo las habitaciones via webhook PMS. La tabla
canónica `hotel` tiene muchas columnas (nombre, direccion, etc.) que pms NO usa.
Aquí mapeamos solo `id` (varchar) para FK + relationships.
"""
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.database import Base


class Hotel(Base):
    __tablename__ = "hotel"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)

    habitaciones = relationship("Habitacion", back_populates="hotel")
    pms_properties = relationship("PMSProperty", back_populates="hotel")
