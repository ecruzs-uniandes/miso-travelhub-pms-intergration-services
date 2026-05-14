import uuid
from sqlalchemy import Column, Integer, DateTime, Date, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, GUID


class Availability(Base):
    __tablename__ = "availability"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # FK a habitacion canónica (varchar id)
    habitacionId = Column("habitacionId", String, ForeignKey("habitacion.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    unidades_disponibles = Column(Integer, nullable=False, default=0)
    unidades_reservadas = Column(Integer, nullable=False, default=0)
    ultima_actualizacion = Column(DateTime, default=func.now())
    fuente_actualizacion = Column(String(50))

    habitacion = relationship("Habitacion", back_populates="availability")

    __table_args__ = (
        UniqueConstraint("habitacionId", "fecha", name="uq_habitacion_date"),
        {"extend_existing": True},
    )
