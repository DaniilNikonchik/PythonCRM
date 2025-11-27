from sqlalchemy.orm import Session
from app.models import Operator, Source, Lead, LeadContact, OperatorCompetence
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


# CRUD операции для операторов
def create_operator(db: Session, name: str, email: str, max_load: int = 10, is_active: bool = True):
    operator = Operator(name=name, email=email, max_load=max_load, is_active=is_active)
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator

def get_operators(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Operator).offset(skip).limit(limit).all()

def update_operator_load(db: Session, operator_id: int, max_load: int):
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if operator:
        operator.max_load = max_load
        db.commit()
        db.refresh(operator)
    return operator

def toggle_operator_active(db: Session, operator_id: int, is_active: bool):
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if operator:
        operator.is_active = is_active
        db.commit()
        db.refresh(operator)
    return operator

# CRUD операции для источников
def create_source(db: Session, name: str, description: str = ""):
    source = Source(name=name, description=description)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source

def get_sources(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Source).offset(skip).limit(limit).all()

# Настройка распределения по источникам
def set_operator_competence(db: Session, operator_id: int, source_id: int, weight: int):
    # Проверяем, существует ли уже компетенция
    competence = db.query(OperatorCompetence).filter(
        OperatorCompetence.operator_id == operator_id,
        OperatorCompetence.source_id == source_id
    ).first()
    
    if competence:
        competence.weight = weight
    else:
        competence = OperatorCompetence(
            operator_id=operator_id,
            source_id=source_id,
            weight=weight
        )
        db.add(competence)
    
    db.commit()
    db.refresh(competence)
    return competence

def get_source_competences(db: Session, source_id: int):
    return db.query(OperatorCompetence).filter(
        OperatorCompetence.source_id == source_id
    ).all()

# Просмотр состояния
def get_leads_with_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Lead).offset(skip).limit(limit).all()

def get_operator_stats(db: Session, operator_id: int):
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        return None
    
    current_load = db.query(LeadContact).filter(
        LeadContact.operator_id == operator_id,
        LeadContact.status.in_(["new", "in_progress"])
    ).count()
    
    total_assigned = db.query(LeadContact).filter(
        LeadContact.operator_id == operator_id
    ).count()
    
    return {
        'operator': operator,
        'current_load': current_load,
        'total_assigned': total_assigned,
        'load_percentage': (current_load / operator.max_load * 100) if operator.max_load > 0 else 0
    }