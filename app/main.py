from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import engine, get_db, Base
from app import models
from app.crud import *
from app.distribution import LeadDistributor
from pydantic import BaseModel
import logging
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем таблицы
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lead Distribution CRM", version="1.0.0")

# Pydantic модели для запросов и ответов
class OperatorBase(BaseModel):
    name: str
    email: str
    max_load: int = 10
    is_active: bool = True

    class Config:
        from_attributes = True

class OperatorResponse(OperatorBase):
    id: int

class SourceBase(BaseModel):
    name: str
    description: str = ""

    class Config:
        from_attributes = True

class SourceResponse(SourceBase):
    id: int

class CompetenceSet(BaseModel):
    operator_id: int
    source_id: int
    weight: int

class CompetenceResponse(CompetenceSet):
    id: int

class ContactCreate(BaseModel):
    external_id: str
    source_id: int
    phone: Optional[str] = None
    email: Optional[str] = None
    message: str = ""

# Модели для ответов
class ContactResponse(BaseModel):
    id: int
    lead_id: int
    source_id: int
    operator_id: Optional[int]
    message: str
    status: str

    class Config:
        from_attributes = True

class OperatorContactResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

class ContactDistributionResponse(BaseModel):
    contact: ContactResponse
    assigned_operator: Optional[OperatorContactResponse]
    status: str

# Эндпоинты для операторов
@app.post("/operators/", response_model=OperatorResponse)
def create_operator_endpoint(operator: OperatorBase, db: Session = Depends(get_db)):
    try:
        return create_operator(db, operator.name, operator.email, operator.max_load, operator.is_active)
    except Exception as e:
        logger.error(f"Error creating operator: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/operators/", response_model=List[OperatorResponse])
def read_operators(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_operators(db, skip, limit)

@app.put("/operators/{operator_id}/load", response_model=OperatorResponse)
def update_operator_load(operator_id: int, max_load: int, db: Session = Depends(get_db)):
    operator = update_operator_load(db, operator_id, max_load)
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    return operator

@app.put("/operators/{operator_id}/active", response_model=OperatorResponse)
def toggle_operator_active(operator_id: int, is_active: bool, db: Session = Depends(get_db)):
    operator = toggle_operator_active(db, operator_id, is_active)
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    return operator

# Эндпоинты для источников
@app.post("/sources/", response_model=SourceResponse)
def create_source_endpoint(source: SourceBase, db: Session = Depends(get_db)):
    try:
        return create_source(db, source.name, source.description)
    except Exception as e:
        logger.error(f"Error creating source: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources/", response_model=List[SourceResponse])
def read_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_sources(db, skip, limit)

# Эндпоинты для настройки распределения
@app.post("/competences/", response_model=CompetenceResponse)
def set_competence(competence: CompetenceSet, db: Session = Depends(get_db)):
    try:
        return set_operator_competence(db, competence.operator_id, competence.source_id, competence.weight)
    except Exception as e:
        logger.error(f"Error setting competence: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources/{source_id}/competences/")
def get_source_competences_endpoint(source_id: int, db: Session = Depends(get_db)):
    return get_source_competences(db, source_id)

# Основной эндпоинт для регистрации обращения
@app.post("/contacts/", response_model=ContactDistributionResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    try:
        result_contact, operator = LeadDistributor.distribute_lead(
            db, contact.source_id, contact.external_id, contact.phone, contact.email, contact.message
        )
        
        # Преобразуем в Pydantic модели для корректной сериализации
        contact_response = ContactResponse(
            id=result_contact.id,
            lead_id=result_contact.lead_id,
            source_id=result_contact.source_id,
            operator_id=result_contact.operator_id,
            message=result_contact.message,
            status=result_contact.status
        )
        
        operator_response = None
        if operator:
            operator_response = OperatorContactResponse(
                id=operator.id,
                name=operator.name,
                email=operator.email
            )
        
        return ContactDistributionResponse(
            contact=contact_response,
            assigned_operator=operator_response,
            status="assigned" if operator else "no_operator_available"
        )
        
    except Exception as e:
        logger.error(f"Error creating contact: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Эндпоинты для просмотра состояния
@app.get("/leads/")
def read_leads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    leads = get_leads_with_contacts(db, skip, limit)
    # Упрощаем ответ для избежания проблем с сериализацией
    simplified_leads = []
    for lead in leads:
        simplified_contacts = []
        for contact in lead.contacts:
            simplified_contacts.append({
                "id": contact.id,
                "source_id": contact.source_id,
                "operator_id": contact.operator_id,
                "message": contact.message,
                "status": contact.status,
                "created_at": contact.created_at.isoformat() if contact.created_at else None
            })
        
        simplified_leads.append({
            "id": lead.id,
            "external_id": lead.external_id,
            "phone": lead.phone,
            "email": lead.email,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "contacts": simplified_contacts
        })
    
    return simplified_leads

@app.get("/operators/{operator_id}/stats/")
def get_operator_stats_endpoint(operator_id: int, db: Session = Depends(get_db)):
    stats = get_operator_stats(db, operator_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    # Упрощаем ответ
    return {
        "operator": {
            "id": stats['operator'].id,
            "name": stats['operator'].name,
            "email": stats['operator'].email,
            "is_active": stats['operator'].is_active,
            "max_load": stats['operator'].max_load
        },
        "current_load": stats['current_load'],
        "total_assigned": stats['total_assigned'],
        "load_percentage": stats['load_percentage']
    }

@app.get("/")
def read_root():
    return {"message": "Lead Distribution CRM API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)