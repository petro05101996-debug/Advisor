# Полная инструкция пользователя — Integration Architect Pro v4.7

Инструмент помогает системному аналитику или бизнес-пользователю предварительно спроектировать интеграцию или проверить текущее интеграционное решение. Это не LLM и не «магический архитектор», а детерминированный rule-engine: он задаёт вопросы, выводит архитектурные требования из бизнес-контекста, подбирает паттерны, показывает риски и формирует черновик архитектурного решения.

---

## 1. Что умеет инструмент

Инструмент помогает:

- спроектировать простую REST/API-интеграцию;
- спроектировать сложную E2E-цепочку с несколькими системами;
- выбрать, где нужна Saga / Process Manager, Kafka, очередь, Outbox, Inbox, DLQ;
- понять, когда нужен кэш, read model, BFF, CQRS-like read path;
- проверить webhook/callback-интеграции;
- учесть DWH/ETL/CDC/регуляторную отчётность;
- учесть legacy/file/SOAP-интеграции;
- проверить текущую production-интеграцию на риски;
- сформировать основу для ADR, обсуждения с архитектором или разработчиком.

Инструмент **не заменяет архитектурное ревью** и не гарантирует production-ready дизайн без проверки специалистом.

---

## 2. Как запустить

### Требования

Нужен установленный Python 3.10+.

### Запуск

Откройте папку проекта и выполните:

```bash
python integration_architect_pro.py
```

После запуска откройте в браузере:

```text
http://127.0.0.1:8110/
```

Если порт занят, освободите порт `8110` или измените порт в коде.

---

## 3. Как проверить, что всё работает

В папке проекта выполните:

```bash
python -m py_compile integration_architect_pro.py
python test_integration_architect.py
python test_sa_full_coverage.py
python test_rank_guard.py
```

Ожидаемый результат:

```text
18/18 regression tests passed
16/16 full SA scenario tests passed
3/3 rank guard tests passed
```

---

## 4. Какой режим выбрать

В интерфейсе есть два режима.

### Простой режим

Используйте его, если пользователь не знает архитектурные термины. Это верхний блок:

```text
Заполнение для человека, который не знает архитектурные термины
```

Он подходит для:

- бизнес-заказчика;
- начинающего аналитика;
- быстрого черновика;
- работы с телефона;
- ситуации, когда нужно быстро получить направление решения.

### Расширенный режим

Нажмите:

```text
Я аналитик, покажи всё
```

Этот режим подходит для:

- системного аналитика;
- архитектора;
- сложного E2E-процесса;
- аудита production-интеграции;
- точного описания систем, шагов, ошибок, SLA, DWH, legacy, source of truth.

---

## 5. Быстрый путь для новичка

### Шаг 1. Выберите ситуацию

Выберите карточку, которая ближе всего к задаче:

```text
Просто передать данные
Показать статус клиенту
Оформить заявку/заказ
Деньги/лимиты/договор
Ждём ответ от внешней системы
Отчётность/DWH
Старая система/файлы/SOAP
Собрать экран из разных систем
Проверить текущее решение
```

Не нужно знать заранее, нужен ли Kafka, Redis, Saga или Outbox. Нужно выбрать бизнес-ситуацию.

### Шаг 2. Напишите название задачи

Пример:

```text
Клиент оформляет кредитную заявку и видит статус в мобильном приложении
```

### Шаг 3. Перечислите системы через запятую

Пример:

```text
mobile app, API заявок, сервис заявок, БКИ, скоринг, CRM, DWH
```

Можно писать обычными словами. Не обязательно идеально.

### Шаг 4. Выберите нагрузку

Варианты:

```text
низкая
средняя
высокая
пиковая
```

Если не знаете — выберите `средняя`. Если есть массовый клиентский экран или частые запросы — выберите `высокая` или `пиковая`.

### Шаг 5. Ответьте, что важнее

Выберите, что хуже:

```text
медленный ответ
устаревшие данные
одинаково критично
не знаю
```

Это помогает понять, нужен ли кэш/read model или лучше ходить напрямую в источник.

### Шаг 6. Можно ли показывать не самые свежие данные

Пример:

```text
можно до 1 минуты
```

Если это деньги, договор, лимит или юридически значимый процесс — чаще нужна строгая актуальность на критичном участке.

### Шаг 7. Есть ли деньги или юридический риск

Отметьте, если процесс влияет на:

- деньги;
- лимиты;
- договоры;
- юридически значимые действия;
- регуляторную отчётность;
- персональные данные.

### Шаг 8. Стабильны ли внешние системы

Если внешние API часто тормозят, падают или отвечают нестабильно, система предложит:

```text
timeout
retry with backoff
circuit breaker
queue
fallback
manual recovery
```

### Шаг 9. Укажите примерное число шагов

Пример:

```text
1 шаг
2–3 шага
4–7 шагов
8+ шагов / сложная цепочка
```

Если процесс: заявка → проверка → скоринг → CRM → уведомления → DWH, то это сложная цепочка.

### Шаг 10. Нажмите кнопку

```text
Собрать черновик из ответов
```

Система автоматически заполнит технические поля и подготовит основу для отчёта.

---

## 6. Как пользоваться расширенным режимом

Расширенный режим нужен, если вы хотите описать интеграцию точнее.

### 6.1. Тип задачи

Выберите:

```text
new_from_scratch — проектирование с нуля
extend_existing_process — расширение текущего процесса
audit_existing_solution — аудит текущей интеграции
```

### 6.2. Бизнес-ситуации

Отметьте все подходящие ситуации. Их может быть несколько.

Пример для кредитной заявки:

```text
application_or_order_creation
client_status_screen
financial_operation
multi_step_business_process
external_api_dependency
webhook_callback
dwh_reporting
legacy_integration
personal_data_exchange
regulatory_process
strict_ordering_required
long_running_process
peak_load_process
exactly_once_required
unstable_external_provider
```

Важно: сложный кейс почти всегда состоит из нескольких бизнес-ситуаций.

### 6.3. Матрица систем

Формат:

```text
name | role | owner | criticality | channel | blocking | sla
```

Пример:

```text
mobile app | client | digital | high | HTTPS | yes | 300ms
API заявок | api | backend | critical | REST | yes | 300ms
сервис заявок | core | backend | critical | REST/Kafka | yes | 500ms
БКИ | external | partner | high | REST/callback | no | 5s
скоринг | decision | risk | critical | REST | yes | 1s
CRM | downstream | sales | medium | Kafka | no | async
DWH | analytics | data | medium | CDC/ETL | no | daily
```

Если вставите заголовок таблицы, инструмент должен его игнорировать.

### 6.4. Матрица шагов процесса

Формат:

```text
level | order | parent | step | system | channel | input | output | timeout | retry | compensation | blocking | owner
```

Пример:

```text
1 | 1 | root | принять заявку | API заявок | REST | анкета | applicationId | 300ms | no | cancel_draft | yes | backend
1 | 2 | root | создать процесс | сервис заявок | REST | applicationId | processId | 500ms | safe | rollback | yes | backend
2 | 3 | process | запросить БКИ | БКИ | REST | personId | requestId | 5s | yes | manual_review | no | risk
2 | 4 | process | принять callback БКИ | API заявок | webhook | reportId | report_saved | 30s | yes | replay | no | backend
2 | 5 | process | антифрод | антифрод | REST | applicationId | fraud_result | 1s | yes | manual_review | yes | risk
2 | 6 | process | скоринг | скоринг | REST | applicationId | score | 1s | yes | manual_review | yes | risk
2 | 7 | process | создать договор в legacy ABS | legacy ABS | SOAP | decision | contractId | 10s | yes | manual_recovery | yes | corebank
2 | 8 | process | отправить событие в CRM | Kafka | event | status_changed | async | yes | replay | no | sales
2 | 9 | process | выгрузить в DWH | DWH | CDC/ETL | events | mart | daily | yes | backfill | no | data
```

### 6.5. Матрица ошибок

Опишите, где возможны сбои.

Формат можно упростить, главное указать:

```text
where | error | detection | retry | fallback | owner
```

Пример:

```text
БКИ | callback не пришёл | timeout watcher | polling retry | manual review | risk
Kafka | consumer lag | lag metric | scale consumers | pause non-critical | platform
legacy ABS | SOAP timeout | timeout/error rate | retry with backoff | manual recovery | corebank
DWH | late events | reconciliation | backfill | data correction | data
```

---

## 7. Как читать отчёт

### 7.1. Главная архитектура

Это основной каркас решения. Например:

```text
Fan-out/Fan-in Orchestrated Process
```

или:

```text
Basic API + DB
Financial Operation State Machine
Webhook Intake + Inbox Processing
Data Pipeline / DWH
```

Для сложного процесса главный вариант должен описывать core-flow, а не частный слой.

### 7.2. Слои архитектуры

В сложных кейсах смотрите не только главный вариант, но и составную архитектуру:

```text
Входной контур
Core process
Async/events
External adapters
Read path/cache
DWH/data
Security/privacy
Observability/SRE
```

Пример правильной интерпретации:

```text
Главная архитектура: Saga / Process Manager
Слой callback: Webhook + Inbox
Слой legacy: SOAP Adapter
Слой DWH: CDC/ETL
Слой клиентского экрана: Status Read Model + Cache
```

### 7.3. Score и confidence

Не путайте:

```text
Score варианта — насколько паттерн подходит под признаки.
Confidence/readiness — насколько можно доверять рекомендации по качеству входных данных.
```

Если readiness низкий, рекомендация предварительная.

### 7.4. Hard warnings

Это самые важные предупреждения. Их нельзя игнорировать.

Примеры:

```text
Деньги + кэш/устаревание
Speed vs strict freshness vs unstable external API
Retry без idempotency
DWH блокирует core-flow
Нет source of truth
Нет статусов для клиентского процесса
```

### 7.5. Открытые вопросы

Это список того, что нужно уточнить перед финальным проектированием. Например:

```text
Какой source of truth?
Какой SLA внешнего API?
Что делать, если callback не пришёл?
Какой ключ идемпотентности?
Какая допустимая свежесть данных?
Кто владелец ручного восстановления?
```

---

## 8. Типовые сценарии и что должен предложить инструмент

### 8.1. Простая REST-интеграция

Бизнес-ситуация:

```text
Система А отправляет данные в систему Б, один шаг, низкая нагрузка.
```

Ожидаемое решение:

```text
Basic API + DB
REST
валидация
логирование
correlationId
error model
простая идемпотентность для POST при необходимости
```

### 8.2. Клиентский экран статуса

Бизнес-ситуация:

```text
Клиент часто смотрит статус заявки. Ответ нужен быстро. Допустимо отставание до 1 минуты.
```

Ожидаемое решение:

```text
Status Read Model
Cache / short TTL
last_updated
fallback stale data
async update
Outbox/Inbox
DLQ
```

### 8.3. Финансовая операция

Бизнес-ситуация:

```text
Операция влияет на деньги, лимит, договор или обязательства.
```

Ожидаемое решение:

```text
Operation table
Idempotency key
State machine
Audit log
Transactional Outbox
Reconciliation
Manual recovery
```

Важно: кэш нельзя использовать для финального финансового решения.

### 8.4. Сложная E2E-цепочка

Бизнес-ситуация:

```text
Много шагов, несколько внешних систем, fan-out/fan-in, компенсации, долгий процесс.
```

Ожидаемое решение:

```text
Saga / Process Manager
State machine
Outbox
Inbox
DLQ
Timeout watcher
Manual recovery
Status history
CorrelationId
```

### 8.5. Webhook/callback

Бизнес-ситуация:

```text
Внешняя система присылает результат позже.
```

Ожидаемое решение:

```text
Webhook Gateway
Signature validation
Inbox
external_event_id
idempotent processing
replay
timeout watcher
reconciliation/polling fallback
```

### 8.6. DWH/регуляторная отчётность

Бизнес-ситуация:

```text
Нужно выгружать данные в отчётность, аналитику или регуляторный контур.
```

Ожидаемое решение:

```text
CDC/ETL/ELT
staging
lineage
data quality checks
reconciliation
backfill
late events handling
```

DWH не должен блокировать core/client flow.

### 8.7. Legacy/file/SOAP

Бизнес-ситуация:

```text
Есть старая система, SOAP, файлы, БД без API или ночные batch-выгрузки.
```

Ожидаемое решение:

```text
Adapter / Anti-Corruption Layer
File Gateway / SOAP Adapter
manifest/checksum
staging
retry schedule
manual reconciliation
rate limit/circuit breaker
```

### 8.8. Multi-source aggregation / карточка 360

Бизнес-ситуация:

```text
Один экран собирается из нескольких систем.
```

Ожидаемое решение:

```text
BFF/API Composition
partial response
timeout per source
freshness per block
fallback
или read model, если нужна высокая скорость
```

---

## 9. Что делать, если отчёт кажется неправильным

Проверьте:

1. Заполнены ли бизнес-ситуации.
2. Не указали ли вы legacy/DWH/webhook как основную задачу, хотя это только часть E2E.
3. Есть ли systems matrix.
4. Есть ли process steps.
5. Указаны ли деньги/регуляторика/ПДн.
6. Указаны ли latency/freshness/load.
7. Указан ли source of truth.
8. Указано ли, что делать при сбое.

Если данных мало, инструмент должен снижать confidence или блокировать результат.

---

## 10. Как использовать результат в работе системного аналитика

Результат можно использовать как основу для:

- обсуждения с архитектором;
- постановки задачи разработчикам;
- ADR;
- описания интеграционного решения;
- требований к API;
- требований к событиям;
- требований к мониторингу;
- списка открытых вопросов;
- ревью текущей production-интеграции.

Рекомендуемый порядок:

```text
1. Собрать бизнес-контекст.
2. Сформировать черновик.
3. Проверить hard warnings.
4. Уточнить открытые вопросы.
5. Доработать systems/process/error matrix.
6. Сгенерировать отчёт.
7. Обсудить с архитектором/разработчиком.
8. Зафиксировать итог в ADR.
```

---

## 11. Ограничения

Инструмент не делает автоматически:

- точный capacity planning;
- расчёт Kafka partitions;
- расчёт размеров БД и индексов;
- финальный security design;
- финальный cloud/infrastructure design;
- юридическую экспертизу;
- замену архитектора.

Он помогает определить класс решения, риски, недостающие требования и архитектурные слои.

---

## 12. Минимальный набор данных для хорошего результата

Для хорошей рекомендации желательно заполнить:

```text
бизнес-цель
тип бизнес-ситуации
список систем
основные шаги
нагрузку
latency SLA
freshness requirement
source of truth
что делать при ошибке
есть ли деньги/ПДн/регуляторика
есть ли DWH/legacy/webhook
нужен ли порядок событий
нужна ли идемпотентность
```

Если этого нет, результат должен считаться предварительным.

---

## 13. Пример полного сложного кейса

### Ввод

```text
Клиент оформляет кредитную заявку в мобильном приложении.
Заявка проходит KYC, БКИ, антифрод, скоринг, legacy ABS, CRM.
БКИ возвращает результат callback-ом.
Клиент видит статус заявки.
Данные уходят в DWH и регуляторную отчётность.
Есть деньги, ПДн, строгий порядок по applicationId.
Нагрузка высокая: 1200 RPS, пик x10.
Клиентский статус должен открываться до 300 мс.
Статус может отставать до 1 минуты.
```

### Ожидаемый вывод

```text
Главная архитектура:
Fan-out/Fan-in Orchestrated Process / Saga / Process Manager

Слои:
API Gateway + idempotency key
Application aggregate / operation table
Process Manager / state machine
Outbox + Kafka/Queue
Inbox + DLQ + replay
Webhook Intake для БКИ callback
External API adapters
SOAP Adapter для legacy ABS
Status Read Model + Cache + last_updated
DWH/CDC/ETL + reconciliation
Audit + PII masking
SRE metrics + stuck process watcher
Manual recovery
```

### Важные предупреждения

```text
Кэш нельзя использовать для финального финансового решения.
DWH не должен блокировать core-flow.
Callback должен быть идемпотентным.
Все внешние вызовы должны иметь timeout/retry/circuit breaker.
Нужна сверка/reconciliation.
```

---

## 14. Рекомендуемое позиционирование инструмента

Правильно:

```text
Инструмент предварительного архитектурного анализа интеграций для системных аналитиков.
```

Неправильно:

```text
Автоматический архитектор, который сам проектирует production-ready систему.
```

---

## 15. Что делать дальше после отчёта

После отчёта нужно:

1. Проверить все hard warnings.
2. Ответить на открытые вопросы.
3. Уточнить SLA, RPS, peak factor, объёмы данных.
4. Согласовать source of truth.
5. Согласовать статусы процесса.
6. Согласовать retry/DLQ/manual recovery.
7. Согласовать security/privacy.
8. Согласовать SRE-метрики.
9. Подготовить ADR.
10. Передать на архитектурное ревью.


---

# Дополнение v4.8.1: Product UX, Quality Gate, ADR, Capacity Lite

## Что изменилось

Версия v4.8 превращает отчёт из простого списка рекомендаций в структурированное архитектурное решение.

Добавлены разделы:

1. **Quality gate требований** — показывает, достаточно ли данных для проектирования.
2. **Главная архитектура и внутренние слои** — отделяет top-level решение от частных слоёв.
3. **MVP-вариант** — минимально безопасный старт.
4. **Production-вариант** — промышленная версия с recovery, monitoring, tests, security.
5. **Почему не выбраны опасные альтернативы** — антипаттерны и trade-offs.
6. **Capacity planning lite** — первичная оценка нагрузки.
7. **Проверка текущего состояния против целевого** — какие контроли отсутствуют.
8. **Отчёты для ролей** — бизнес/аналитик/разработчик/архитектор.
9. **ADR export** — готовая основа для архитектурного решения.
10. **Дополнительные диаграммы** — context, event flow, data flow, failure flow.

## Как использовать Quality Gate

Если отчёт пишет `blocked` или `risky`, не надо сразу отдавать решение в разработку.

Сначала нужно ответить на вопросы из блока **“Критично уточнить”**:

- кто source of truth;
- кто владелец процесса;
- нужна ли статусная модель;
- какой idempotency key;
- допустима ли устаревшая информация;
- что делать при сбое внешней системы;
- как делать DWH/reconciliation;
- какой ключ порядка событий;
- какие поля являются ПДн.

## Как читать MVP и Production

**MVP-вариант** — это минимальный безопасный набор для первого релиза.

**Production-вариант** — то, что нужно добавить до промышленной эксплуатации: Saga, Outbox/Inbox, DLQ, replay, monitoring, runbook, security, failover, load tests.

## Как использовать ADR export

Раздел **ADR export** можно копировать в Confluence/документацию:

- Контекст;
- Решение;
- Альтернативы;
- Последствия.

После копирования его нужно дополнить конкретными ссылками на контракты, диаграммы, владельцев и SLA.

## Как использовать Capacity planning lite

Это не финальный sizing, а первичная проверка реалистичности.

Поля:

- `RPS/TPS`;
- `peak factor`;
- `payload_kb`;
- `retention_days`;
- `target_lag_seconds`.

Инструмент считает:

- peak RPS;
- поток MB/s;
- GB/day;
- стартовый порядок partitions/workers;
- заметки по backpressure, retention, ordering, DWH.

Финальный capacity plan всё равно должен делать архитектор/разработчик с реальными метриками и железом.

## Как использовать отчёты для ролей

В поле **“Для кого сформировать отчёт”** можно выбрать:

- бизнес;
- системный аналитик;
- разработчик;
- архитектор;
- полный отчёт для всех.

Это меняет акценты в разделе “Отчёты для ролей”.

## Главная идея v4.8

Инструмент больше не просто отвечает “нужен REST/Kafka/Saga”.

Он помогает пройти путь:

```text
сырая бизнес-задача
→ качество требований
→ главная архитектура
→ внутренние слои
→ MVP/Production
→ ADR
→ диаграммы
→ чеклист ревью
```
