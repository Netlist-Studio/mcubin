from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from mcubin.database import Base


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    barcode: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    mpn: Mapped[str | None] = mapped_column(String, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    datasheet: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
