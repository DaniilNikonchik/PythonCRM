from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Operator(Base):
    __tablename__ = "operators"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    max_load = Column(Integer, default=10)
    
    # Исправляем отношения
    competencies = relationship("OperatorCompetence", back_populates="operator", cascade="all, delete-orphan")
    lead_contacts = relationship("LeadContact", back_populates="assigned_operator")

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    phone = Column(String, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Исправляем отношения
    contacts = relationship("LeadContact", back_populates="lead", cascade="all, delete-orphan")

class Source(Base):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    
    # Исправляем отношения
    competencies = relationship("OperatorCompetence", back_populates="source", cascade="all, delete-orphan")
    contacts = relationship("LeadContact", back_populates="source", cascade="all, delete-orphan")

class OperatorCompetence(Base):
    __tablename__ = "operator_competences"
    
    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("operators.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))
    weight = Column(Integer, default=1)
    
    operator = relationship("Operator", back_populates="competencies")
    source = relationship("Source", back_populates="competencies")

class LeadContact(Base):
    __tablename__ = "lead_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))
    operator_id = Column(Integer, ForeignKey("operators.id"), nullable=True)
    message = Column(String)
    status = Column(String, default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    lead = relationship("Lead", back_populates="contacts")
    source = relationship("Source", back_populates="contacts")
    assigned_operator = relationship("Operator", back_populates="lead_contacts")