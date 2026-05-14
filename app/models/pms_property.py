import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, GUID


class PMSProperty(Base):
    __tablename__ = "pms_properties"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # FK al hotel canónico (varchar id)
    hotel_id = Column(String, ForeignKey("hotel.id"), nullable=False)
    pms_provider = Column(String(100), nullable=False)
    pms_property_id = Column(String(255), nullable=False)
    api_key_hash = Column(String(255))
    webhook_secret_hash = Column(String(255))
    status = Column(String(20), default="active")
    last_sync_at = Column(DateTime)
    sync_error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    hotel = relationship("Hotel", back_populates="pms_properties")

    __table_args__ = (
        UniqueConstraint("pms_provider", "pms_property_id", name="uq_pms_provider_property"),
        {"extend_existing": True},
    )
