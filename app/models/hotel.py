import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, GUID


class Hotel(Base):
    __tablename__ = "hotels"
    __table_args__ = {"extend_existing": True}

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)
    direccion = Column(String(500))
    ciudad = Column(String(100), nullable=False)
    pais = Column(String(5), nullable=False)
    latitud = Column(Float)
    longitud = Column(Float)
    estrellas = Column(Integer)
    pms_proveedor = Column(String(100))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    rooms = relationship("Room", back_populates="hotel")
    pms_properties = relationship("PMSProperty", back_populates="hotel")
