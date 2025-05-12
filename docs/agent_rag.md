# Агентный RAG с механизмом самооценки

Это расширение стандартной RAG-системы, которое добавляет функциональность агентного подхода и механизм самооценки ответов.

## Обзор

Агентный RAG (Retrieval Augmented Generation) расширяет возможности стандартного RAG путем добавления:

1. **Агентной архитектуры** - система может самостоятельно определять необходимые действия и планировать их выполнение
2. **Механизма самооценки** - оценка качества сгенерированных ответов по набору критериев
3. **Автоматического улучшения ответов** - система может улучшать ответы, если они не соответствуют заданному уровню качества

## Архитектура

Агентная система интегрирована в существующую архитектуру RAG с сохранением всех паттернов DDD и CQRS:

```
┌─────────────────────────────┐
│                             │
│      RAG Core System        │
│                             │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│                             │
│       Agent System          │
│                             │
│  ┌─────────┐   ┌─────────┐  │
│  │ Actions │   │ Planning│  │
│  └─────────┘   └─────────┘  │
│                             │
│  ┌─────────┐   ┌─────────┐  │
│  │  State  │   │ Memory  │  │
│  └─────────┘   └─────────┘  │
│                             │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│                             │
│   Self-Assessment System    │
│                             │
│  ┌─────────┐   ┌─────────┐  │
│  │Evaluation│  │Improvement│ │
│  └─────────┘   └─────────┘  │
│                             │
└─────────────────────────────┘
```

## Основные компоненты

### Агентная система

1. **AgentService** - основной сервис для работы с агентами
2. **ActionRegistry** - реестр доступных действий агента
3. **PlanningService** - сервис для планирования действий

### Механизм самооценки

1. **EvaluationService** - сервис для оценки качества ответов и их улучшения
2. **Критерии оценки**:
   - Релевантность (relevance)
   - Фактическая точность (factual_accuracy)
   - Полнота (completeness)
   - Логическая связность (logical_coherence)
   - Соответствие этическим нормам (ethical_compliance)

## Доступные действия агента

1. **search** - поиск информации в векторной базе данных
2. **generate** - генерация ответа на основе контекста
3. **evaluate** - оценка качества ответа
4. **improve** - улучшение ответа на основе результатов оценки

## API

### Создание агента

```
POST /agents
{
  "name": "RAG Assistant",
  "description": "Agent for RAG with self-assessment",
  "conversation_id": "unique-conversation-id"
}
```

### Выполнение запроса через агента

```
POST /agents/{agent_id}/query
{
  "query": "Ваш запрос",
  "use_planning": true  // Опционально, для сложных запросов
}
```

### Оценка ответа

```
POST /agents/{agent_id}/evaluate
{
  "query": "Ваш запрос",
  "response": "Ответ для оценки",
  "context": ["Контекст1", "Контекст2"]
}
```

### Улучшение ответа на основе оценки

```
POST /evaluations/{evaluation_id}/improve
{
  "agent_id": "id-агента"
}
```

## CLI-команды

### Создание агента

```bash
python cli.py agent create --name "Мой агент" --description "Описание агента"
```

### Поиск с использованием агента

```bash
python cli.py query "Ваш запрос" --agent --planning
```

### Оценка ответа

```bash
python cli.py agent evaluate <agent_id> --query "Ваш запрос" --response "Ответ для оценки" --context "Контекст"
```

### Улучшение ответа

```bash
python cli.py agent improve <agent_id> <evaluation_id>
```

## Конфигурация

Настройки агентной системы и механизма самооценки находятся в файле `app/config/base.yaml`:

```yaml
# Agent configuration
agent:
  default_agent_name: "RAG Assistant"
  default_agent_description: "Agent for RAG with self-assessment"
  
  actions:
    enabled:
      - "search"
      - "generate"
      - "evaluate"
      - "improve"
  
  planning:
    enabled: true
    max_steps: 10
    timeout: 120  # seconds

# Self-assessment configuration
evaluation:
  thresholds:
    relevance: 0.7
    factual_accuracy: 0.8
    completeness: 0.7
    logical_coherence: 0.7
    ethical_compliance: 0.9
  
  weights:
    relevance: 0.25
    factual_accuracy: 0.3
    completeness: 0.2
    logical_coherence: 0.15
    ethical_compliance: 0.1
  
  overall_threshold: 0.75
  max_improvement_iterations: 2
```

## Расширение системы

### Добавление новых действий агента

1. В `main.py` зарегистрируйте новое действие в `action_registry`:

```python
def custom_action(agent, parameters):
    """Custom action for agent."""
    # Implement your action logic here
    return result

action_registry.register_action(
    "custom_action",
    custom_action,
    {"description": "Description of custom action"}
)
```

### Настройка критериев оценки

Для изменения порогов и весов критериев оценки, обновите соответствующие разделы в конфигурационном файле.

## Примеры использования

### Пример использования агента для сложного запроса с планированием

```python
response = requests.post(
    "http://localhost:8000/agents/my-agent-id/query",
    json={
        "query": "Объясни подробно, как работает система RAG, и какие у нее преимущества по сравнению с чистыми LLM?",
        "use_planning": True
    }
)
```

### Пример оценки ответа

```python
response = requests.post(
    "http://localhost:8000/agents/my-agent-id/evaluate",
    json={
        "query": "Что такое RAG?",
        "response": "RAG - это метод улучшения ответов языковых моделей.",
        "context": ["RAG (Retrieval Augmented Generation) - это техника, которая объединяет поиск информации и генерацию текста для улучшения ответов языковых моделей."]
    }
)
```

### Пример улучшения ответа

```python
response = requests.post(
    "http://localhost:8000/evaluations/eval-id/improve",
    json={"agent_id": "my-agent-id"}
)
```

## Дополнительная информация

Больше примеров и подробной документации по агентной RAG системе можно найти в основной документации проекта.
