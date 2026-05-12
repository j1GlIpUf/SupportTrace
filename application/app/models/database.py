from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime
import os
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user") # "user", "support", "admin"
    department = Column(String, default="Не относится к департаментам")
    
    tickets = relationship("Ticket", back_populates="author")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    status = Column(String, default="open") # "open", "distributed", "closed"
    predicted_classes = Column(String) # Строка названий для истории
    manual_category = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    author = relationship("User", back_populates="tickets")
    assignments = relationship("TicketAssignment", back_populates="ticket", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")

class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    
    # МЕНЯЕМ ТУТ: с Integer на String
    department_name = Column(String, nullable=False) 
    
    is_resolved = Column(Boolean, default=False)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)

    ticket = relationship("Ticket", back_populates="assignments")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    sender = Column(String)
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    ticket = relationship("Ticket", back_populates="messages")
    author = relationship("User")

# Настройки подключения
SQLALCHEMY_DATABASE_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL", 
    "postgresql://sasha:3256@localhost/vkr_db"
)

# 2. Создаем engine. 

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()