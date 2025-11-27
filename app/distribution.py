import random
from sqlalchemy.orm import Session
from app.models import Operator, OperatorCompetence, LeadContact, Lead, Source
import logging

logger = logging.getLogger(__name__)

class LeadDistributor:
    @staticmethod
    def find_or_create_lead(db: Session, external_id: str, phone: str = None, email: str = None):
        """Найти существующего лида или создать нового"""
        try:
            logger.info(f"Поиск/создание лида: external_id={external_id}, phone={phone}, email={email}")
            
            # Поиск по external_id (основной идентификатор)
            if external_id:
                lead = db.query(Lead).filter(Lead.external_id == external_id).first()
                if lead:
                    logger.info(f"Найден существующий лид по external_id: {lead.id}")
                    return lead
            
            # Поиск по телефону
            if phone:
                lead = db.query(Lead).filter(Lead.phone == phone).first()
                if lead:
                    logger.info(f"Найден существующий лид по phone: {lead.id}")
                    return lead
            
            # Поиск по email
            if email:
                lead = db.query(Lead).filter(Lead.email == email).first()
                if lead:
                    logger.info(f"Найден существующий лид по email: {lead.id}")
                    return lead
            
            # Создание нового лида
            logger.info("Создание нового лида")
            lead = Lead(
                external_id=external_id, 
                phone=phone, 
                email=email
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
            logger.info(f"Создан новый лид: {lead.id}")
            return lead
            
        except Exception as e:
            logger.error(f"Ошибка в find_or_create_lead: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_available_operators(db: Session, source_id: int):
        """Получить доступных операторов для источника с учетом нагрузки"""
        try:
            logger.info(f"Поиск доступных операторов для источника: {source_id}")
            
            # Проверяем, существует ли источник
            source = db.query(Source).filter(Source.id == source_id).first()
            if not source:
                logger.warning(f"Источник {source_id} не найден")
                return []
            
            logger.info(f"Источник найден: {source.name}")
            
            # Получаем компетенции для данного источника
            competencies = db.query(OperatorCompetence).filter(
                OperatorCompetence.source_id == source_id
            ).all()
            
            logger.info(f"Найдено компетенций: {len(competencies)}")
            
            available_operators = []
            
            for comp in competencies:
                operator = comp.operator
                logger.info(f"Проверка оператора {operator.id}: активен={operator.is_active}")
                
                # Проверяем, что оператор активен
                if not operator.is_active:
                    logger.info(f"Оператор {operator.id} не активен - пропускаем")
                    continue
                
                # Считаем текущую нагрузку оператора
                current_load = db.query(LeadContact).filter(
                    LeadContact.operator_id == operator.id,
                    LeadContact.status.in_(["new", "in_progress"])
                ).count()
                
                logger.info(f"Оператор {operator.id}: текущая нагрузка={current_load}, лимит={operator.max_load}")
                
                # Проверяем, что оператор не превысил лимит
                if current_load < operator.max_load:
                    available_operators.append({
                        'operator': operator,
                        'weight': comp.weight,
                        'current_load': current_load
                    })
                    logger.info(f"Оператор {operator.id} доступен, вес: {comp.weight}")
                else:
                    logger.info(f"Оператор {operator.id} перегружен - пропускаем")
            
            logger.info(f"Итого доступных операторов: {len(available_operators)}")
            return available_operators
            
        except Exception as e:
            logger.error(f"Ошибка в get_available_operators: {str(e)}")
            return []

    @staticmethod
    def select_operator(available_operators):
        """Выбрать оператора по весовому распределению"""
        try:
            logger.info(f"Выбор оператора из {len(available_operators)} доступных")
            
            if not available_operators:
                logger.info("Нет доступных операторов")
                return None
            
            # Взвешенный случайный выбор
            total_weight = sum(op['weight'] for op in available_operators)
            logger.info(f"Общий вес: {total_weight}")
            
            if total_weight == 0:
                logger.info("Общий вес равен 0, возвращаем первого оператора")
                return available_operators[0]['operator']
            
            random_value = random.uniform(0, total_weight)
            logger.info(f"Случайное значение: {random_value}")
            
            current_weight = 0
            for operator_data in available_operators:
                current_weight += operator_data['weight']
                logger.info(f"Проверка оператора {operator_data['operator'].id}, текущий вес: {current_weight}")
                
                if random_value <= current_weight:
                    logger.info(f"Выбран оператор: {operator_data['operator'].id}")
                    return operator_data['operator']
            
            # На всякий случай возвращаем первого
            logger.info(f"Возвращаем первого оператора: {available_operators[0]['operator'].id}")
            return available_operators[0]['operator']
            
        except Exception as e:
            logger.error(f"Ошибка в select_operator: {str(e)}")
            return available_operators[0]['operator'] if available_operators else None

    @staticmethod
    def distribute_lead(db: Session, source_id: int, external_id: str, 
                       phone: str = None, email: str = None, message: str = ""):
        """Основной метод распределения обращения"""
        try:
            logger.info(f"=== НАЧАЛО РАСПРЕДЕЛЕНИЯ ===")
            logger.info(f"external_id={external_id}, source_id={source_id}, phone={phone}, email={email}")
            
            # 1. Найти или создать лида
            logger.info("Шаг 1: Поиск/создание лида")
            lead = LeadDistributor.find_or_create_lead(db, external_id, phone, email)
            
            # 2. Получить доступных операторов
            logger.info("Шаг 2: Получение доступных операторов")
            available_operators = LeadDistributor.get_available_operators(db, source_id)
            
            # 3. Выбрать оператора
            logger.info("Шаг 3: Выбор оператора")
            selected_operator = LeadDistributor.select_operator(available_operators)
            
            # 4. Создать обращение
            logger.info("Шаг 4: Создание обращения")
            contact = LeadContact(
                lead_id=lead.id,
                source_id=source_id,
                operator_id=selected_operator.id if selected_operator else None,
                message=message,
                status="new" if selected_operator else "no_operator"
            )
            
            db.add(contact)
            db.commit()
            db.refresh(contact)
            
            logger.info(f"=== РАСПРЕДЕЛЕНИЕ ЗАВЕРШЕНО ===")
            logger.info(f"Создано обращение: {contact.id}, оператор: {selected_operator.id if selected_operator else 'None'}")
            
            return contact, selected_operator
            
        except Exception as e:
            logger.error(f"=== ОШИБКА РАСПРЕДЕЛЕНИЯ ===")
            logger.error(f"Ошибка: {str(e)}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            db.rollback()
            raise