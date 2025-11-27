import requests
from collections import Counter
import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.database import SessionLocal, engine
from app.models import Base

BASE_URL = "http://localhost:8000"

def complete_test():
    print("=== ПОЛНОЕ ТЕСТИРОВАНИЕ CRM СИСТЕМЫ ===\n")
    
    # 1. Создаем нескольких операторов
    print("1. СОЗДАЕМ ОПЕРАТОРОВ")
    operators_data = [
        {"name": "Оператор Алиса", "email": "alisa@company.com", "max_load": 5},
        {"name": "Оператор Борис", "email": "boris@company.com", "max_load": 3},
        {"name": "Оператор Виктор", "email": "viktor@company.com", "max_load": 4, "is_active": False}
    ]
    
    operators = []
    for op_data in operators_data:
        response = requests.post(f"{BASE_URL}/operators/", json=op_data)
        operator = response.json()
        operators.append(operator)
        status = "активен" if operator['is_active'] else "НЕ активен"
        print(f"   ✓ {operator['name']} (ID:{operator['id']}) - лимит: {operator['max_load']} - {status}")
    
    # 2. Создаем источники
    print("\n2. СОЗДАЕМ ИСТОЧНИКИ")
    sources_data = [
        {"name": "Telegram Bot", "description": "Основной телеграм бот"},
        {"name": "WhatsApp Bot", "description": "WhatsApp канал"},
        {"name": "Website Form", "description": "Форма на сайте"}
    ]
    
    sources = []
    for source_data in sources_data:
        response = requests.post(f"{BASE_URL}/sources/", json=source_data)
        source = response.json()
        sources.append(source)
        print(f"   ✓ {source['name']} (ID:{source['id']})")
    
    # 3. Настраиваем распределение
    print("\n3. НАСТРАИВАЕМ РАСПРЕДЕЛЕНИЕ")
    competences = [
        # Telegram: Алиса - 10, Борис - 30 (25%/75%)
        {"operator_id": operators[0]['id'], "source_id": sources[0]['id'], "weight": 10},
        {"operator_id": operators[1]['id'], "source_id": sources[0]['id'], "weight": 30},
        
        # WhatsApp: Алиса - 20, Борис - 20 (50%/50%)
        {"operator_id": operators[0]['id'], "source_id": sources[1]['id'], "weight": 20},
        {"operator_id": operators[1]['id'], "source_id": sources[1]['id'], "weight": 20},
        
        # Website: только Алиса
        {"operator_id": operators[0]['id'], "source_id": sources[2]['id'], "weight": 50},
    ]
    
    for comp in competences:
        response = requests.post(f"{BASE_URL}/competences/", json=comp)
        print(f"   ✓ Оператор {comp['operator_id']} -> Источник {comp['source_id']} (вес: {comp['weight']})")
    
    # 4. Тестируем распределение лидов
    print("\n4. ТЕСТИРУЕМ РАСПРЕДЕЛЕНИЕ ЛИДОВ")
    
    test_contacts = [
        # Лиды из Telegram (должны распределяться 25% Алисе, 75% Борису)
        {"external_id": "lead_tg_001", "source_id": sources[0]['id'], "phone": "+79110001111", "message": "Вопрос из Telegram"},
        {"external_id": "lead_tg_002", "source_id": sources[0]['id'], "phone": "+79110002222", "message": "Еще вопрос из TG"},
        {"external_id": "lead_tg_003", "source_id": sources[0]['id'], "phone": "+79110003333", "message": "TG консультация"},
        {"external_id": "lead_tg_004", "source_id": sources[0]['id'], "phone": "+79110004444", "message": "TG помощь"},
        
        # Лиды из WhatsApp (50%/50%)
        {"external_id": "lead_wa_001", "source_id": sources[1]['id'], "phone": "+79120001111", "message": "WhatsApp вопрос"},
        {"external_id": "lead_wa_002", "source_id": sources[1]['id'], "phone": "+79120002222", "message": "WA консультация"},
        
        # Лиды с сайта (только Алиса)
        {"external_id": "lead_web_001", "source_id": sources[2]['id'], "email": "web@test.com", "message": "Заявка с сайта"},
        
        # Повторные обращения одного лида
        {"external_id": "lead_tg_001", "source_id": sources[1]['id'], "phone": "+79110001111", "message": "Тот же лид из WhatsApp"},
    ]
    
    distribution_results = []
    for i, contact in enumerate(test_contacts, 1):
        response = requests.post(f"{BASE_URL}/contacts/", json=contact)
        result = response.json()
        
        operator_name = result['assigned_operator']['name'] if result['assigned_operator'] else "НЕТ ОПЕРАТОРА"
        distribution_results.append({
            'contact_id': i,
            'operator': operator_name,
            'source': next(s['name'] for s in sources if s['id'] == contact['source_id'])
        })
        
        print(f"   ✓ Обращение {i}: {operator_name} <- {contact['external_id']}")
    
    # 5. Анализ распределения
    print("\n5. АНАЛИЗ РАСПРЕДЕЛЕНИЯ")
    operator_counts = Counter([r['operator'] for r in distribution_results])
    for operator, count in operator_counts.items():
        percentage = (count / len(distribution_results)) * 100
        print(f"   {operator}: {count} обращений ({percentage:.1f}%)")
    
    # 6. Проверяем нагрузку операторов
    print("\n6. НАГРУЗКА ОПЕРАТОРОВ")
    for operator in operators[:2]:  # Только активные операторы
        response = requests.get(f"{BASE_URL}/operators/{operator['id']}/stats/")
        stats = response.json()
        load_percent = stats['load_percentage']
        status = "⚡ ПЕРЕГРУЗКА" if load_percent > 100 else "Норма"
        print(f"   {operator['name']}: {stats['current_load']}/{operator['max_load']} ({load_percent:.1f}%) - {status}")
    
    # 7. Проверяем лидов и их обращения
    print("\n7. ЛИДЫ И ИХ ОБРАЩЕНИЯ")
    response = requests.get(f"{BASE_URL}/leads/")
    leads = response.json()
    
    for lead in leads:
        print(f"   Лид '{lead['external_id']}': {len(lead['contacts'])} обращений(я)")
        for contact in lead['contacts']:
            operator_name = "Нет оператора" if not contact['operator_id'] else next(
                op['name'] for op in operators if op['id'] == contact['operator_id']
            )
            source_name = next(s['name'] for s in sources if s['id'] == contact['source_id'])
            print(f"     - {source_name}: {operator_name} ('{contact['message']}')")
    
    print("\n=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
    print(f"Всего создано: {len(operators)} операторов, {len(sources)} источников, {len(leads)} лидов, {len(test_contacts)} обращений")

if __name__ == "__main__":
    complete_test()