# Примеры использования агентного RAG

В этом документе приведены примеры использования агентного RAG с механизмом самооценки в различных сценариях.

## Базовый пример использования

### 1. Создание агента

```python
import requests
import json
import uuid

# Базовый URL API
API_URL = "http://localhost:8000"

# Создание нового агента
conversation_id = str(uuid.uuid4())
response = requests.post(
    f"{API_URL}/agents",
    json={
        "name": "RAG Assistant",
        "description": "Agent for answering questions about AI",
        "conversation_id": conversation_id
    }
)

agent_data = response.json()
agent_id = agent_data["id"]
print(f"Created agent with ID: {agent_id}")
```

### 2. Простой запрос

```python
# Выполнение запроса через агента
query_response = requests.post(
    f"{API_URL}/agents/{agent_id}/query",
    json={
        "query": "Что такое RAG и как он работает?",
        "use_planning": False  # Для простых запросов не требуется планирование
    }
)

result = query_response.json()
print(f"Response: {result['response']}")

# Вывод информации об оценке, если она была выполнена
if "evaluation" in result:
    print(f"Evaluation Score: {result['evaluation']['overall_score']}")
    print(f"Needs Improvement: {result['evaluation'].get('needs_improvement', False)}")
```

### 3. Ручная оценка ответа

```python
# Оценка качества ответа
evaluation_response = requests.post(
    f"{API_URL}/agents/{agent_id}/evaluate",
    json={
        "query": "Что такое RAG?",
        "response": "RAG - это метод объединения поиска и генерации текста.",
        "context": [
            "RAG (Retrieval Augmented Generation) - это техника, которая объединяет поиск (retrieval) информации и генерацию (generation) текста для улучшения ответов языковых моделей.",
            "RAG помогает преодолеть проблему устаревших знаний в языковых моделях и снижает галлюцинации."
        ]
    }
)

evaluation_result = evaluation_response.json()
print(f"Evaluation ID: {evaluation_result['evaluation_id']}")
print(f"Overall Score: {evaluation_result['overall_score']}")

# Вывод оценок по отдельным критериям
for criterion, data in evaluation_result["criterion_scores"].items():
    print(f"{criterion}: {data['score']} - {data['reason'][:100]}...")
```

### 4. Улучшение ответа

```python
# Улучшение ответа на основе оценки
improvement_response = requests.post(
    f"{API_URL}/evaluations/{evaluation_result['evaluation_id']}/improve",
    json={"agent_id": agent_id}
)

improvement_result = improvement_response.json()
print("Original Response:")
print(improvement_result["original_response"])
print("\nImproved Response:")
print(improvement_result["improved_response"])

# Вывод предложений по улучшению
print("\nImprovement Suggestions:")
for suggestion in improvement_result["suggestions"]:
    print(f"- {suggestion['criterion']} (Priority: {suggestion['priority']}): {suggestion['suggestion']}")
```

## Пример с использованием планирования

Для сложных запросов, требующих многоэтапной обработки:

```python
# Сложный запрос с планированием
complex_query_response = requests.post(
    f"{API_URL}/agents/{agent_id}/query",
    json={
        "query": "Опиши подробно преимущества и недостатки RAG по сравнению с fine-tuning моделей, включая примеры использования и рекомендации по выбору подхода.",
        "use_planning": True  # Включаем планирование для сложного запроса
    }
)

complex_result = complex_query_response.json()

# Вывод плана, если он был создан
if "plan" in complex_result:
    plan = complex_result["plan"]
    print(f"Plan ID: {plan['id']}")
    print(f"Task: {plan['task']}")
    print(f"Status: {plan['status']}")
    
    # Вывод шагов плана
    print("\nPlan Steps:")
    for step in plan["steps"]:
        print(f"{step['step_number']}. {step['action_type']} - {step['status']}")
        print(f"   Description: {step['description']}")

# Вывод ответа
print("\nResponse:")
print(complex_result["response"])
```

## Пример создания специализированного агента

```python
# Создание специализированного агента для работы с конкретной коллекцией документов
specialized_agent_response = requests.post(
    f"{API_URL}/agents",
    json={
        "name": "Research Assistant",
        "description": "Agent specialized in scientific literature",
        "conversation_id": str(uuid.uuid4()),
        "config": {
            "default_collection": "research_papers",
            "evaluation": {
                "thresholds": {
                    "factual_accuracy": 0.9  # Повышенные требования к фактической точности
                }
            }
        }
    }
)

specialized_agent = specialized_agent_response.json()
specialized_agent_id = specialized_agent["id"]
```

## Пример CLI-использования

```bash
# Создание агента
python cli.py agent create --name "Научный ассистент" --description "Агент для работы с научными статьями"

# Выполнение запроса через агента с планированием
python cli.py query "Объясни в деталях, как RAG помогает снизить галлюцинации в языковых моделях и какие методы оценки можно использовать для измерения этого эффекта. Приведи примеры." --agent --agent-id <agent_id> --planning

# Создание плана
python cli.py agent plan <agent_id> "Проанализировать и сравнить различные подходы к RAG, включая BM25, DPR и Hybrid Retrieval" --constraint "Фокус на научной литературе последних двух лет" --constraint "Учитывать метрики производительности"

# Выполнение плана
python cli.py agent execute-plan <agent_id> <plan_id>

# Оценка ответа
python cli.py agent evaluate <agent_id> --query "Как работает RAG?" --response "RAG объединяет поиск и генерацию." --context "RAG (Retrieval Augmented Generation) объединяет внешний поиск информации и генерацию текста языковыми моделями."

# Улучшение ответа
python cli.py agent improve <agent_id> <evaluation_id>
```

## Примеры с использованием различных действий агента

### Выполнение поискового действия

```python
# Выполнение поискового действия напрямую
search_response = requests.post(
    f"{API_URL}/agents/{agent_id}/actions",
    json={
        "action_type": "search",
        "parameters": {
            "query": "Что такое RAG?",
            "collection": "default",
            "limit": 5
        }
    }
)

search_result = search_response.json()
print(f"Search action ID: {search_result['id']}")
print(f"Status: {search_result['status']}")

# Вывод найденных источников
for i, source in enumerate(search_result["result"], 1):
    print(f"Source {i}: {source['title']} (Score: {source['score']})")
    print(f"Content: {source['content'][:100]}...")
```

### Выполнение генерации ответа

```python
# Выполнение действия генерации ответа
generate_response = requests.post(
    f"{API_URL}/agents/{agent_id}/actions",
    json={
        "action_type": "generate",
        "parameters": {
            "query": "Что такое RAG?",
            "context": [
                "RAG (Retrieval Augmented Generation) - это техника, которая объединяет поиск информации и генерацию текста для улучшения ответов языковых моделей.",
                "RAG помогает преодолеть проблему устаревших знаний в языковых моделях и снижает галлюцинации."
            ],
            "language": "ru"
        }
    }
)

generate_result = generate_response.json()
print(f"Generated Response: {generate_result['result']}")
```

## Пример полного цикла с самооценкой и улучшением

```python
# Полный цикл: поиск -> генерация -> оценка -> улучшение

# 1. Выполнение поиска
search_action = requests.post(
    f"{API_URL}/agents/{agent_id}/actions",
    json={
        "action_type": "search",
        "parameters": {
            "query": "Какие существуют методы оценки качества RAG систем?",
            "collection": "research_papers",
            "limit": 5
        }
    }
).json()

retrieved_context = search_action["result"]
context_texts = [item["content"] for item in retrieved_context]

# 2. Генерация ответа
generate_action = requests.post(
    f"{API_URL}/agents/{agent_id}/actions",
    json={
        "action_type": "generate",
        "parameters": {
            "query": "Какие существуют методы оценки качества RAG систем?",
            "context": context_texts
        }
    }
).json()

initial_response = generate_action["result"]

# 3. Оценка ответа
evaluate_action = requests.post(
    f"{API_URL}/agents/{agent_id}/actions",
    json={
        "action_type": "evaluate",
        "parameters": {
            "query": "Какие существуют методы оценки качества RAG систем?",
            "response": initial_response,
            "context": context_texts
        }
    }
).json()

evaluation_result = evaluate_action["result"]
print(f"Evaluation Score: {evaluation_result['overall_score']}")
print(f"Needs Improvement: {evaluation_result['needs_improvement']}")

# 4. Улучшение ответа (если требуется)
if evaluation_result["needs_improvement"]:
    improve_action = requests.post(
        f"{API_URL}/agents/{agent_id}/actions",
        json={
            "action_type": "improve",
            "parameters": {
                "query": "Какие существуют методы оценки качества RAG систем?",
                "response": initial_response,
                "context": context_texts,
                "evaluation": evaluation_result
            }
        }
    ).json()
    
    improved_response = improve_action["result"]["improved_response"]
    print("\nImproved Response:")
    print(improved_response)
else:
    print("\nResponse (no improvement needed):")
    print(initial_response)
```

## Кастомизация процесса самооценки

```python
# Создание агента с кастомными настройками оценки
custom_evaluation_agent = requests.post(
    f"{API_URL}/agents",
    json={
        "name": "Quality-Focused Assistant",
        "description": "Agent with custom evaluation settings",
        "conversation_id": str(uuid.uuid4()),
        "config": {
            "evaluation": {
                # Кастомные пороги для критериев
                "thresholds": {
                    "relevance": 0.8,
                    "factual_accuracy": 0.9,
                    "completeness": 0.8,
                    "logical_coherence": 0.8,
                    "ethical_compliance": 0.95
                },
                # Кастомные веса для общей оценки
                "weights": {
                    "relevance": 0.2,
                    "factual_accuracy": 0.4,  # Больший вес для фактической точности
                    "completeness": 0.2,
                    "logical_coherence": 0.15,
                    "ethical_compliance": 0.05
                },
                # Более высокий общий порог
                "overall_threshold": 0.85,
                # Больше итераций улучшения
                "max_improvement_iterations": 3
            }
        }
    }
).json()

custom_agent_id = custom_evaluation_agent["id"]
```

Эти примеры демонстрируют различные сценарии использования агентного RAG с механизмом самооценки. Вы можете адаптировать их под свои конкретные задачи и интегрировать в свои приложения.
