from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from mcubin.database import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    parts: Mapped[list["Part"]] = relationship("Part", back_populates="location_obj")


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mpn: Mapped[str | None] = mapped_column(String, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    supplier: Mapped[str | None] = mapped_column(String)
    supplier_pn: Mapped[str | None] = mapped_column(String, index=True)
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("locations.id"), nullable=True)
    location_obj: Mapped[Optional["Location"]] = relationship("Location", back_populates="parts")
    category: Mapped[str | None] = mapped_column(String)
    datasheet: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def location(self) -> str | None:
        return self.location_obj.name if self.location_obj else None
