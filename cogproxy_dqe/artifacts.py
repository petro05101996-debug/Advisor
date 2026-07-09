from __future__ import annotations

"""User-facing deterministic artifacts for CogProxy DQE.

The offline core must be useful to the user, not only technically elegant.
These generators create concrete artifacts from the user's text: architecture
skeletons, QA test cases, traceability, risks, APIs, storage and MVP plans.
They are heuristic and honest; receipt still marks them as offline-scaffolded
unless a model/source/test verifier is attached.
"""

from dataclasses import dataclass
import re
from typing import Dict, List, Sequence, Tuple

from .models import TaskContract


@dataclass
class Requirement:
    req_id: str
    text: str
    source_ref: str
    kind: str = "functional"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" -•\t\n")


def split_input_lines(text: str) -> List[Tuple[str, str]]:
    lines: List[Tuple[str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        cleaned = _clean(line)
        if cleaned:
            lines.append((f"input:L{i}", cleaned))
    if not lines and text.strip():
        lines.append(("input:L1", _clean(text)))
    return lines


def extract_statuses(text: str) -> List[str]:
    statuses = set()
    not_status = {"API", "HTTP", "JSON", "XML", "REST", "SLA", "URL", "UUID", "ID"}
    for m in re.finditer(r"\b[A-Z][A-Z0-9_]{2,}\b", text):
        token = m.group(0)
        if token not in not_status:
            statuses.add(token)
    lower = text.lower()
    for s in ["новый", "активен", "закрыт", "отменён", "отменен", "успешно", "ошибка", "завершён", "завершен", "обработка", "ожидание"]:
        if s in lower:
            statuses.add(s.upper())
    return sorted(statuses)


def extract_domain_terms(text: str, limit: int = 12) -> List[str]:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9_\-]{4,}", text)
    stop = {
        "нужно", "надо", "должен", "должна", "должны", "сделать", "проверить",
        "спроектируй", "проанализируй", "сервис", "систему", "система", "который",
        "которая", "пользователь", "пользователя", "требуется", "через", "если",
        "чтобы", "данные", "статус", "статусы", "ошибка", "может", "нельзя",
        "required", "should", "must", "service", "system", "status",
    }
    counts: Dict[str, int] = {}
    for word in words:
        key = word.strip("_-").lower()
        if len(key) < 4 or key in stop:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]


def choose_primary_object(text: str) -> str:
    lower = text.lower()
    if "автоплат" in lower:
        return "автоплатёж"
    if "заяв" in lower:
        return "заявка"
    if "заказ" in lower:
        return "заказ"
    if "документ" in lower:
        return "документ"
    if "api" in lower:
        return "API-операция"
    if "плат" in lower or "оплат" in lower:
        return "платёж"
    return "целевая операция"


def guess_entities(text: str) -> List[str]:
    lower = text.lower()
    entities: List[str] = []
    mapping = [
        ("автоплат", ["Autopayment", "PaymentSchedule", "PaymentAttempt"]),
        ("опиф", ["Fund", "InvestmentAccount", "PurchaseApplication"]),
        ("заяв", ["Application", "ApplicationStatus", "ApplicationDecision"]),
        ("заказ", ["Order", "OrderItem", "OrderStatus"]),
        ("достав", ["Delivery", "Courier", "DeliveryStatus"]),
        ("платеж", ["Payment", "PaymentOperation", "PaymentStatus"]),
        ("оплат", ["Payment", "PaymentOperation", "PaymentStatus"]),
        ("документ", ["Document", "DocumentRevision", "EditOperation"]),
        ("редакт", ["Document", "EditOperation", "CollaborationSession"]),
        ("api", ["APIRequest", "APIResponse", "IdempotencyKey"]),
        ("клиент", ["Client", "ClientProfile"]),
        ("пользователь", ["User", "UserProfile"]),
        ("фонд", ["Fund", "FundRule"]),
        ("лимит", ["Limit", "LimitRule"]),
        ("реестр", ["RegistryRecord", "RegistryStatus"]),
    ]
    for marker, items in mapping:
        if marker in lower:
            entities.extend(items)
    if not entities:
        terms = extract_domain_terms(text, 4)
        entities.extend(["UserRequest", "TargetEntity", "Operation", "StatusEvent"])
        entities.extend([term[:1].upper() + term[1:] for term in terms[:2]])
    out: List[str] = []
    for item in entities:
        if item not in out:
            out.append(item)
    return out[:10]


def extract_requirements(text: str) -> List[Requirement]:
    source_lines = split_input_lines(text)
    candidates: List[Tuple[str, str]] = []
    req_markers = ["долж", "нужно", "треб", "если", "при ", "возвращ", "статус", "ошиб", "api", "sla", "нельзя", "обяз", "валид", "провер", "must", "should", "shall", "return", "status", "error"]
    for ref, line in source_lines:
        for piece in re.split(r"(?<=[.!?])\s+|;\s+", line):
            cleaned = _clean(piece)
            if len(cleaned) < 12:
                continue
            if any(marker in cleaned.lower() for marker in req_markers):
                candidates.append((ref, cleaned))
    if not candidates:
        candidates.append(("input:L1", f"Из запроса следует необходимость: {choose_primary_object(text)} должен иметь проверяемый результат и понятные ошибки."))
    requirements: List[Requirement] = []
    seen = set()
    for ref, req_text in candidates:
        norm = req_text.lower()
        if norm in seen:
            continue
        seen.add(norm)
        kind = "business_rule"
        if any(x in norm for x in ["api", "возвращ", "status", "статус", "http"]):
            kind = "api_behavior"
        elif any(x in norm for x in ["ошиб", "нельзя", "fail", "error"]):
            kind = "negative_rule"
        requirements.append(Requirement(f"R-{len(requirements)+1:03d}", req_text, ref, kind))
    return requirements[:20]


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    h = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(str(cell).replace("\n", "<br>") for cell in row) + " |" for row in rows]
    return "\n".join([h, sep, *body])


def generate_requirements_qa_artifact(contract: TaskContract) -> Tuple[str, Dict[str, object]]:
    task = contract.source_text or contract.goal
    reqs = extract_requirements(task)
    statuses = extract_statuses(task)
    obj = choose_primary_object(task)
    req_rows = [[r.req_id, r.kind, r.text, r.source_ref] for r in reqs]

    positive_cases: List[List[str]] = []
    for i, req in enumerate(reqs, start=1):
        positive_cases.append([
            f"TC-{i:03d}", req.req_id, "positive",
            f"Сервис доступен; данные для '{obj}' валидны.",
            "1. Отправить запрос/выполнить действие по требованию.\n2. Проверить ответ, состояние и аудит.",
            f"Поведение соответствует требованию: {req.text}",
        ])
    base = len(positive_cases)
    negatives = [
        ("invalid_input", f"Передать некорректные или неполные данные для '{obj}'.", "Операция отклонена; состояние не меняется; возвращается диагностируемая ошибка."),
        ("wrong_status", f"Выполнить действие, когда '{obj}' находится в неподходящем статусе.", "Операция запрещена; причина отказа явно указана; финальные статусы не перезаписываются."),
        ("duplicate_request", "Повторить тот же запрос с тем же idempotency/correlation ключом.", "Дубликат не создаёт вторую операцию; возвращается прежний результат или безопасный отказ."),
        ("external_timeout", "Сымитировать таймаут/ошибку внешнего сервиса.", "Система фиксирует ошибку, не теряет событие, возможен retry/DLQ или ручной разбор."),
    ]
    negative_cases: List[List[str]] = []
    for j, (code, steps, expected) in enumerate(negatives, start=1):
        target = reqs[min(j - 1, len(reqs) - 1)].req_id if reqs else "R-000"
        negative_cases.append([f"TC-{base+j:03d}", target, code, "negative", steps, expected])

    open_questions = [
        f"Какие точные допустимые статусы у '{obj}' до и после операции?",
        "Какие коды/формат ошибок должен вернуть API для каждого отказа?",
        "Нужна ли идемпотентность и какой ключ считается уникальным?",
        "Какие поля обязательны, какие лимиты и граничные значения?",
    ]
    if statuses:
        open_questions.insert(0, "Подтвердить полную status model: " + ", ".join(statuses))

    coverage = []
    for req in reqs:
        tc_ids = [tc[0] for tc in positive_cases if tc[1] == req.req_id] + [tc[0] for tc in negative_cases if tc[1] == req.req_id]
        coverage.append([req.req_id, ", ".join(tc_ids) or "нет", "draft"])

    answer = (
        f"# Ответ DQE\n\n"
        f"## Цель проверки\nПользовательская задача: {contract.goal}\n\n"
        "Результат ниже — стартовый QA-артефакт: нормализованные требования, тест-кейсы, негативные ветки и вопросы к аналитику/владельцу сервиса.\n\n"
        f"## Нормализованные требования\n{table(['ID', 'Тип', 'Требование', 'Источник'], req_rows)}\n\n"
        "## Сценарии\n- Positive path: валидный запрос/действие приводит к ожидаемому результату и сохраняет аудит.\n- Alternative path: действие запрещено из-за неподходящего статуса, но система возвращает объяснимый отказ.\n- Error path: неверные данные, дубль запроса, таймаут внешнего сервиса или неизвестный статус.\n\n"
        f"## Тест-кейсы\n{table(['TC', 'Req', 'Тип', 'Предусловия', 'Шаги', 'Ожидаемый результат'], positive_cases)}\n\n"
        f"## Негативные проверки\n{table(['TC', 'Req', 'Проверка', 'Тип', 'Шаги', 'Ожидаемый результат'], negative_cases)}\n\n"
        f"## Покрытие требований\n{table(['Требование', 'Покрыто тестами', 'Минимальный статус'], coverage)}\n\n"
        "## Риски и вопросы\n" + "\n".join(f"- {q}" for q in open_questions) +
        "\n\n## Отчёт\nСтатус: можно начинать тест-дизайн, но до автопрогона нужны точные контракты API, статусы, ошибки и тестовые данные.\n"
    )
    return answer, {"requirements": [r.__dict__ for r in reqs], "positive_cases": positive_cases, "negative_cases": negative_cases, "statuses": statuses, "open_questions": open_questions}


def _entity_responsibility(entity: str) -> str:
    lower = entity.lower()
    if "status" in lower:
        return "Текущий статус и допустимые переходы."
    if "payment" in lower:
        return "Попытка списания/оплаты, результат и идемпотентность."
    if "application" in lower:
        return "Заявка-основание и её жизненный цикл."
    if "document" in lower or "revision" in lower:
        return "Содержимое, версия и история изменений."
    return "Бизнес-сущность, состояние и связи с операциями."


def _entity_storage_note(entity: str) -> str:
    lower = entity.lower()
    if "status" in lower:
        return "История переходов и актуальный статус."
    if "payment" in lower:
        return "Сумма, попытки, resultCode, внешние id."
    if "application" in lower:
        return "Связь с клиентом, статус, основание операции."
    if "document" in lower or "operation" in lower:
        return "Версия, операция, порядок применения."
    return "Атрибуты, связи, createdAt/updatedAt, version."


def _table_name(entity: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", entity).lower()


def generate_system_design_artifact(contract: TaskContract) -> Tuple[str, Dict[str, object]]:
    task = contract.source_text or contract.goal
    entities = guess_entities(task)
    obj = choose_primary_object(task)
    statuses = extract_statuses(task)
    terms = extract_domain_terms(task)

    if "Autopayment" in entities:
        endpoints = [
            ["POST", "/autopayments", "Создать/подключить автоплатёж после проверок заявки, клиента, фонда и суммы."],
            ["GET", "/autopayments/{id}", "Получить состояние, schedule, последнюю попытку списания и причину отключения."],
            ["POST", "/autopayments/{id}/disable", "Отключить автоплатёж идемпотентно."],
            ["POST", "/payment-attempts/{id}/callback", "Принять результат списания/покупки и обновить операцию."],
        ]
        state_model = "DRAFT → VALIDATING → ACTIVE → SUSPENDED → DISABLED; попытка списания: PLANNED → PROCESSING → SUCCESS/FAILED/RETRY_WAIT."
    elif "Document" in entities:
        endpoints = [
            ["POST", "/documents", "Создать документ и начальную ревизию."],
            ["POST", "/documents/{id}/operations", "Принять операцию редактирования с clientRevision и idempotencyKey."],
            ["GET", "/documents/{id}/snapshot", "Получить актуальный snapshot и номер ревизии."],
            ["GET", "/documents/{id}/events", "Получить stream операций после указанной ревизии."],
        ]
        state_model = "Document: ACTIVE/ARCHIVED; Operation: RECEIVED → ORDERED → APPLIED/REJECTED; Snapshot строится из подтверждённых операций."
    else:
        slug = re.sub(r"\s+", "-", obj)
        endpoints = [["POST", f"/{slug}s", f"Создать или запустить операцию для '{obj}'."], ["GET", f"/{slug}s/{{id}}", "Получить состояние и диагностические поля."], ["POST", f"/{slug}s/{{id}}/cancel", "Отменить операцию, если статус допускает отмену."]]
        state_model = "NEW → VALIDATING → PROCESSING → SUCCESS/FAILED/CANCELLED. Финальные статусы не перезаписываются."

    invariants = [
        f"{obj.capitalize()} не переходит в финальный успешный статус без выполненных бизнес-проверок.",
        "Повторный запрос с тем же idempotencyKey не создаёт вторую бизнес-операцию.",
        "Позднее событие не может изменить CANCELLED/FAILED/SUCCESS без отдельной компенсирующей операции.",
        "Каждое внешнее взаимодействие имеет correlationId и audit trail.",
    ]
    if "Autopayment" in entities:
        invariants.insert(0, "Автоплатёж нельзя активировать, если связанная заявка закрыта, отклонена или не прошла проверки фонда/клиента/суммы.")

    entity_rows = [[e, _entity_responsibility(e)] for e in entities]
    db_rows = [[_table_name(e), "OLTP", _entity_storage_note(e)] for e in entities[:7]] + [["outbox_event", "OLTP", "Надёжная публикация событий после изменения состояния."], ["inbox_event", "OLTP", "Защита от дублей входящих callback/event."], ["audit_log", "append-only", "Кто/когда/почему изменил состояние."]]
    risks = [["Дубль команды", "Две активные операции/списания", "idempotencyKey + unique constraint + inbox."], ["Поздний callback", "Перезапись финального статуса", "state guard: разрешённые переходы только из актуального состояния."], ["Недоступность внешнего сервиса", "Зависшая операция", "timeout, retry policy, DLQ/manual review, явный FAILED/RETRY_WAIT."], ["Слишком тяжёлая архитектура", "Latency и стоимость без пользы", "Сначала минимальный вертикальный срез; Kafka/outbox только для критичных событий."]]
    if statuses:
        risks.append(["Неявная status model", "Разные команды понимают статусы по-разному", "Зафиксировать допустимые переходы: " + ", ".join(statuses)])

    critical_flow = [
        f"1. API принимает команду по объекту '{obj}' и валидирует обязательные поля.",
        "2. Сервис проверяет текущий статус из собственного источника истины, а не доверяет данным клиента.",
        "3. Изменение состояния и запись outbox выполняются в одной транзакции.",
        "4. Внешние вызовы выполняются за пределами транзакции с retry, timeout и идемпотентностью.",
        "5. Callback/event обрабатывается через inbox и проверку актуальности состояния.",
        "6. Метрики, аудит и алерты фиксируют задержки, ошибки, дубли и ручные разборы.",
    ]

    answer = (
        f"# Ответ DQE\n\n## Цель и границы\nЗадача пользователя: {contract.goal}\n\n"
        f"Проектируем минимально достаточное ядро для объекта **{obj}**, а не абстрактную архитектуру. UI, BI и сложная ML-логика вне первого ядра, если пользователь отдельно не требует.\n\n"
        "## Участники и сценарии\n- Инициатор: клиент/оператор/внешний сервис, который запускает изменение состояния.\n- Core service: владеет состоянием объекта и правилами переходов.\n- External systems: платёжный шлюз, фонд/реестр, документный сервис или иной внешний участник.\n- Support/audit: разбирает DLQ, спорные статусы и ручные корректировки.\n\n"
        f"Ключевые термины из запроса: {', '.join(terms) if terms else 'явных доменных терминов мало'}.\n\n"
        "## Инварианты и SLA\n" + "\n".join(f"- {x}" for x in invariants) +
        "\n\nSLA на MVP: синхронный API отвечает быстро и не ждёт долгих внешних операций; долгие действия переводятся в async-операцию с прозрачным статусом. Конкретные цифры надо задать после оценки нагрузки.\n\n"
        f"## Данные и состояния\nState model: **{state_model}**\n\n{table(['Сущность', 'Ответственность'], entity_rows)}\n\n"
        "## Архитектура\nМинимальная схема:\n\n```text\nClient/API Gateway\n  → Core Service\n      → OLTP DB (state + idempotency + audit)\n      → Outbox Publisher\n          → Event Bus / Queue\n              → External Integration Workers\n                  → Inbox + Callback Handler\n```\n\n"
        "Синхронным оставляем только то, без чего нельзя принять команду: аутентификация, валидация, проверка текущего состояния и запись команды. Внешние вызовы и побочные эффекты — асинхронно, если они могут тормозить или падать.\n\n"
        f"## API и контракты\n{table(['Метод', 'Endpoint', 'Назначение'], endpoints)}\n\nОбязательные поля для команд: `idempotencyKey`, `correlationId`, `actorId`, `objectId`, `requestedAt`, payload с бизнес-данными.\n\n"
        f"## Хранение\n{table(['Таблица', 'Тип', 'Зачем'], db_rows)}\n\n"
        "## Критические потоки\n" + "\n".join(critical_flow) +
        f"\n\n## Отказы и риски\n{table(['Риск', 'Последствие', 'Защита'], risks)}\n\n"
        "## План реализации\n1. Зафиксировать state machine и запрещённые переходы.\n2. Описать API contract и ошибки.\n3. Реализовать Core Service + OLTP + idempotency.\n4. Добавить outbox/inbox для внешних событий.\n5. Подготовить негативные тесты: дубли, поздние события, таймауты, неверные статусы.\n6. Добавить метрики: latency API, pending operations, retries, DLQ, conflict count.\n\n"
        "## Что не надо делать в MVP\n- Не добавлять Kafka/микросервисы только ради enterprise-архитектуры.\n- Не доверять статусу из фронта или callback без проверки актуального состояния.\n- Не прятать ошибки внешних интеграций под общий SUCCESS.\n"
    )
    return answer, {"entities": entities, "statuses": statuses, "endpoints": endpoints, "db_tables": db_rows, "invariants": invariants, "risks": risks}


def generate_research_analysis_artifact(contract: TaskContract) -> Tuple[str, Dict[str, object]]:
    task = contract.source_text or contract.goal
    terms = extract_domain_terms(task)
    risks = [["Толпа агентов", "Много одинакового шума вместо качества", "Разные роли + независимые критерии + reducer."], ["Нет verifier'а", "Нельзя доказать улучшение", "Claim-level статусы: supported/unsupported/contradicted/unverifiable."], ["Универсальность обещана слишком широко", "Пользователь разочаруется", "Единое ядро + domain packs, а не гарантия для любых задач."], ["Стоимость/latency", "Пользователь не будет ждать ради простого вопроса", "Adaptive modes: fast/standard/deep/audit."]]
    metrics = [["rubric_quality", "Оценка ответа по фиксированной рубрике", "главная метрика пользы"], ["missed_critical_issues", "Сколько критичных рисков пропущено", "важнее красивого текста"], ["unsupported_claim_rate", "Доля claims без источника/проверки", "антигаллюцинация"], ["repair_success_rate", "Сколько дефектов исправлено после verifier", "проверяет смысл repair loop"], ["cost_latency", "Цена и время ответа", "ограничение продуктовой применимости"]]
    mvp = ["Сделать ядро single-machine: contract, graph, worker pool, claims, verifiers, reducer, receipt.", "Добавить 3 полезных pack'а: system_design, requirements_qa, research_analysis.", "Ввести честные статусы: scaffold_only, model_checked, source_verified, test_verified.", "Сделать compare-режим: one-shot vs DQE на одном task и на папке задач.", "Запустить 30–50 задач и считать uplift, а не спорить по ощущениям."]
    answer = (
        "# Ответ DQE\n\n## Тезис\n"
        "Гипотеза жизнеспособна только если горизонтально масштабируется не число агентов, а проверяемый процесс качества: split → parallel attempts → claims → verification → repair → reduce.\n\n"
        f"Пользовательский запрос: {contract.goal}\n\n"
        "## Что подтверждается\n- Идея сильная на уровне execution framework: можно системно улучшать сложные ответы через декомпозицию, независимую критику, claims и проверку.\n- Самая перспективная область — профессиональные задачи с критериями: требования, QA, system design, анализ документов, код, архитектурные решения.\n"
        f"- Термины из запроса: {', '.join(terms) if terms else 'явных терминов мало'}.\n\n"
        "## Что не доказано\n- Не доказан кратный прирост качества без реальной внешней LLM и A/B-бенчмарка.\n- Не доказана универсальность как гарантия: для субъективных задач verifier слабый.\n- Не доказана окупаемость deep/audit режима по cost/latency.\n\n"
        "## Архитектура решения\n```text\nUser task → TaskContract → Pack Planner → Workers → Claim Store → Verifier Mesh → Repair Loop → Reducer → Final Answer + Quality Receipt\n```\n\n"
        f"## Критика\n{table(['Риск', 'Почему опасно', 'Что сделать'], risks)}\n\n"
        "## MVP\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(mvp, start=1)) +
        f"\n\n## Метрики проверки\n{table(['Метрика', 'Что измеряет', 'Зачем'], metrics)}\n\n"
        "## Вывод\nДелать стоит, но продавать как универсальный усилитель мышления рано. Правильное позиционирование: проверяемый quality execution layer для сложных профессиональных ответов. Первый критерий успеха — измеримый uplift на задачах пользователя.\n"
    )
    return answer, {"risks": risks, "metrics": metrics, "mvp": mvp, "terms": terms}


def generate_universal_artifact(contract: TaskContract) -> Tuple[str, Dict[str, object]]:
    task = contract.source_text or contract.goal
    terms = extract_domain_terms(task)
    obj = choose_primary_object(task)
    answer = (
        f"# Ответ DQE\n\n## Цель\nПонять и решить пользовательскую задачу: {contract.goal}\n\n"
        "## Ключевые выводы\n"
        f"- Основной объект работы: **{obj}**.\n"
        f"- Важные термины из запроса: {', '.join(terms) if terms else 'явных доменных терминов мало'}.\n"
        "- Без внешней модели и источников результат является структурированным черновиком, а не финальной экспертной истиной.\n\n"
        "## Решение\n1. Зафиксировать ожидаемый пользовательский результат и критерии качества.\n2. Разбить задачу на проверяемые части.\n3. Сформировать первичный артефакт, а не список общих советов.\n4. Проверить риски, пропуски, противоречия и неподтверждённые утверждения.\n5. Выдать отчёт с уровнем доверия.\n\n"
        "## Риски\n- Если критерии качества не заданы, система может улучшить структуру, но не смысл.\n- Если нет источников или тестов, claims остаются неподтверждёнными.\n- Для сложной предметной области нужен domain pack или внешний provider.\n\n"
        "## Следующие шаги\n- Запустить DQE в подходящем pack'е: `system_design`, `requirements_qa` или `research_analysis`.\n- Для проверки пользы использовать `compare`, чтобы увидеть разницу one-shot vs DQE.\n- Для реального качества подключить внешний CLI provider или передать документы/требования.\n"
    )
    return answer, {"terms": terms, "primary_object": obj}


def generate_user_artifact(contract: TaskContract) -> Tuple[str, Dict[str, object]]:
    if contract.pack_name == "system_design":
        return generate_system_design_artifact(contract)
    if contract.pack_name == "requirements_qa":
        return generate_requirements_qa_artifact(contract)
    if contract.pack_name == "research_analysis":
        return generate_research_analysis_artifact(contract)
    return generate_universal_artifact(contract)
