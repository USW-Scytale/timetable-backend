from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class Building(Base):
    __tablename__ = "buildings"

    building_id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(10), nullable=True)
    total_rooms = Column(Integer, default=0)

    rooms = relationship("Room", back_populates="building")


class Room(Base):
    __tablename__ = "rooms"

    room_id = Column(String(20), primary_key=True)
    building_id = Column(String(20), ForeignKey("buildings.building_id"), nullable=False)
    name = Column(String(50), nullable=False)
    capacity = Column(Integer, default=30)
    tags = Column(JSON, nullable=True)

    building = relationship("Building", back_populates="rooms")
    schedules = relationship("CourseSchedule", back_populates="room")
