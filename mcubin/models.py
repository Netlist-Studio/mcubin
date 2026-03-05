from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from mcubin.database import Base

PROVIDERS = ["mouser", "digikey"]


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    parts: Mapped[list["Part"]] = relationship("Part", back_populates="location_obj")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)  # see PROVIDERS
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parts: Mapped[list["Part"]] = relationship("Part", back_populates="supplier_obj")


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mpn: Mapped[str | None] = mapped_column(String, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    supplier_pn: Mapped[str | None] = mapped_column(String, index=True)
    supplier_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("suppliers.id"), nullable=True)
    supplier_obj: Mapped[Optional["Supplier"]] = relationship("Supplier", back_populates="parts")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("locations.id"), nullable=True)
    location_obj: Mapped[Optional["Location"]] = relationship("Location", back_populates="parts")
    category: Mapped[str | None] = mapped_column(String)
    datasheet: Mapped[str | None] = mapped_column(String)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)
    rohs_status: Mapped[str | None] = mapped_column(String, nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_breaks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    supplier_data_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def location(self) -> str | None:
        return self.location_obj.name if self.location_obj else None

    @property
    def supplier(self) -> str | None:
        return self.supplier_obj.name if self.supplier_obj else None
