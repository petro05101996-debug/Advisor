from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, List, Tuple

from .artifacts import generate_user_artifact
from .bug_analysis import run_bug_analysis
from .models import TaskContract, WorkerResult
from .packs import default_registry
from .providers import BaseProvider, DeterministicProvider, ProviderError


def decompose_task(contract: TaskContract) -> WorkerResult:
    pack = default_registry().get(contract.pack_name)
    parts = []
    for section in contract.required_sections:
        guidance = pack.section_guidance.get(section, "Раскрыть секцию по цели пользователя.")
        parts.append(f"- {section}: {guidance}")
    content = "Декомпозиция задачи по контракту качества:\n" + "\n".join(parts)
    return WorkerResult(
        worker_name="decomposer",
        role="decompose",
        content=content,
        artifacts={"sections": contract.required_sections, "guidance": pack.section_guidance},
        confidence=0.85,
    )


def _pack_specific_seed(contract: TaskContract) -> Dict[str, str]:
    if contract.pack_name == "system_design":
        return {
            "Цель и границы": "Зафиксировать бизнес-цель, входящие и исключённые сценарии, границы ответственности компонентов.",
            "Участники и сценарии": "Выделить клиента/оператора/внешние сервисы, основные и альтернативные сценарии.",
            "Инварианты и SLA": "Назвать главный инвариант, целевую задержку, допустимую деградацию и условия отказа.",
            "Данные и состояния": "Описать ключевые сущности, статусы, источник истины, идемпотентные ключи и аудит.",
            "Архитектура": "Предложить минимально достаточные сервисы, синхронные вызовы только на критическом пути, асинхронные события для побочных эффектов.",
            "Критические потоки": "Изолировать оплату/подтверждение/изменение состояния, добавить idempotency, outbox/inbox, retry и DLQ там, где они нужны.",
            "Отказы и риски": "Проверить дубли, гонки, таймауты, частичные отказы, рассинхронизацию статусов и невозможность отката.",
            "План реализации": "Сначала контракт API и state machine, затем минимальный вертикальный срез, затем нагрузка, мониторинг и негативные сценарии.",
        }
    if contract.pack_name == "requirements_qa":
        return {
            "Цель проверки": "Проверить требования на полноту, непротиворечивость, тестопригодность и покрытие критических веток.",
            "Нормализованные требования": "Разложить исходный текст на атомарные требования с уникальными идентификаторами.",
            "Сценарии": "Сформировать positive path, альтернативные ветки и ошибочные ветки по состояниям.",
            "Тест-кейсы": "Для каждого требования дать предусловие, шаги, данные, ожидаемый результат и проверяемый артефакт.",
            "Негативные проверки": "Проверить неверные статусы, повторные запросы, пустые поля, лимиты, таймауты, недоступность внешних сервисов.",
            "Покрытие требований": "Сделать матрицу требование → сценарий → тест-кейс → ожидаемый результат.",
            "Риски и вопросы": "Вынести неоднозначные формулировки, отсутствующие статусы, неописанные ошибки и непроверяемые правила.",
            "Отчёт": "Дать статус готовности документации к тестированию и список блокеров.",
        }
    if contract.pack_name == "research_analysis":
        return {
            "Тезис": "Сформулировать проверяемую гипотезу, а не лозунг.",
            "Что подтверждается": "Указать, какие части идеи логически или эмпирически поддержаны.",
            "Что не доказано": "Отделить недоказанные ожидания: универсальность, кратный прирост, стоимость, latency, устойчивость.",
            "Архитектура решения": "Описать ядро: contract compiler, graph runtime, workers, claims, verifiers, repair, reducer, receipt.",
            "Критика": "Показать слабые места: отсутствие verifier, дороговизна, переусложнение, ложная уверенность, слабая проверка субъективных задач.",
            "MVP": "Сделать single-machine kernel с 2–3 domain packs и A/B harness до распределённого кластера.",
            "Метрики проверки": "Считать uplift по рубрике, hallucination rate, missed critical issues, latency, cost, repair success rate.",
            "Вывод": "Идея жизнеспособна как quality execution framework, но не как универсальная магия для любых ответов.",
        }
    return {
        "Цель": "Понять, какой результат нужен пользователю и какие ограничения важны.",
        "Ключевые выводы": "Сжато назвать главное.",
        "Решение": "Предложить рабочую структуру решения.",
        "Риски": "Назвать ограничения и места, где подход может сломаться.",
        "Следующие шаги": "Дать конкретные проверяемые действия.",
    }


def generate_candidate(contract: TaskContract, provider: BaseProvider) -> WorkerResult:
    """Generate the primary user-facing artifact.

    v0.2 makes the offline fallback useful: system_design produces a concrete
    architecture draft, requirements_qa produces test cases and traceability,
    research_analysis produces critique/MVP/metrics. External provider output
    is appended as additional material, not trusted blindly.
    """
    if contract.pack_name == "bug_analysis":
        return run_bug_analysis(contract, provider)

    content, artifacts = generate_user_artifact(contract)
    used_provider = not isinstance(provider, DeterministicProvider)

    if used_provider:
        prompt = build_generation_prompt(contract)
        try:
            provider_answer = provider.complete(prompt, role="generator")
            content += (
                "\n\n## Черновик внешней модели\n"
                "Ниже сохранён ответ provider'а. DQE не принимает его как истину: "
                "утверждения всё равно попадают в claims и проверяются по доступным эвристикам.\n\n"
                + provider_answer.strip()
            )
            artifacts["external_provider_answer"] = provider_answer.strip()
        except ProviderError as exc:
            content += (
                "\n\n## Ошибка внешнего provider'а\n"
                f"{exc}. Использован полезный offline fallback; receipt ограничит доверие к результату."
            )
            artifacts["provider_error"] = str(exc)
            used_provider = False

    return WorkerResult(
        worker_name="generator",
        role="generate",
        content=content,
        artifacts=artifacts,
        confidence=0.62 if not used_provider else 0.74,
        used_provider=used_provider,
    )


def build_generation_prompt(contract: TaskContract) -> str:
    if contract.pack_name == "bug_analysis":
        return (
            "Ты worker в distributed quality engine. Помоги найти root cause бага по логам, stacktrace, коду и документации.\n"
            "Не фантазируй. Отделяй evidence от гипотез. Дай минимальный fix и regression tests.\n\n"
            f"Цель пользователя: {contract.goal}\n"
        )
    return (
        "Ты worker в distributed quality engine. Дай содержательный черновик ответа.\n"
        "Не пиши финальный маркетинговый текст, пиши проверяемые тезисы.\n\n"
        f"Цель пользователя: {contract.goal}\n"
        f"Тип задачи: {contract.task_type}\n"
        f"Обязательные секции: {', '.join(contract.required_sections)}\n"
        f"Критерии успеха: {', '.join(contract.success_criteria)}\n"
    )


def critique_candidate(contract: TaskContract, candidate: str) -> WorkerResult:
    missing = [s for s in contract.required_sections if f"## {s}" not in candidate]
    critique: List[str] = []
    if missing:
        critique.append("Не хватает секций: " + ", ".join(missing))
    else:
        critique.append("Все обязательные секции присутствуют.")
    if "риск" not in candidate.lower() and "отказ" not in candidate.lower():
        critique.append("Слабая зона: недостаточно явно раскрыты риски/ограничения.")
    if "метрик" not in candidate.lower() and contract.pack_name == "research_analysis":
        critique.append("Слабая зона: для исследовательской задачи нужны метрики проверки.")
    if "инвариант" not in candidate.lower() and contract.pack_name == "system_design":
        critique.append("Слабая зона: для system design нужен главный инвариант.")
    if len(candidate.split()) < 120:
        critique.append("Ответ слишком короткий для сложной задачи.")
    return WorkerResult(
        worker_name="critic",
        role="criticize",
        content="\n".join(f"- {c}" for c in critique),
        artifacts={"missing_sections": missing},
        confidence=0.76,
    )


def counterexample_worker(contract: TaskContract) -> WorkerResult:
    risks = []
    if contract.pack_name == "system_design":
        risks = [
            "Архитектура может стать избыточной, если добавить Kafka/outbox/DLQ без критической необходимости.",
            "Главный инвариант может быть нарушен поздним событием после отмены или повторным запросом.",
            "SLA может быть заявлен без расчёта худшего сценария нагрузки.",
        ]
    elif contract.pack_name == "requirements_qa":
        risks = [
            "Тесты могут покрыть happy path, но пропустить переходы статусов и ошибки внешних сервисов.",
            "Требование может быть формально описано, но непроверяемо из-за отсутствия ожидаемого результата.",
            "Дубли и повторные вызовы могут не попасть в negative coverage.",
        ]
    elif contract.pack_name == "research_analysis":
        risks = [
            "Горизонтальное масштабирование может увеличить стоимость без прироста, если нет сильного verifier'а.",
            "Большинство агентов может усиливать общий bias, а не исправлять ошибку.",
            "Универсальность может оказаться только framework-level, а не guarantee-level.",
        ]
    else:
        risks = [
            "Задача может быть слишком субъективной для строгой проверки.",
            "Без критериев качества система может создать ложную уверенность.",
            "Полная обработка может быть дороже, чем ценность ответа.",
        ]
    return WorkerResult(
        worker_name="counterexample",
        role="counterexample",
        content="\n".join(f"- {r}" for r in risks),
        artifacts={"counterexamples": risks},
        confidence=0.7,
    )


def evidence_worker(contract: TaskContract) -> WorkerResult:
    lines = [line.strip() for line in contract.source_text.splitlines() if line.strip()]
    explicit = []
    for idx, line in enumerate(lines, start=1):
        lower = line.lower()
        if any(marker in lower for marker in ["http", "согласно", "требование", "должен", "нужно", "sla", "api", "статус", "ошибка"]):
            explicit.append({"ref": f"input:L{idx}", "text": line[:500]})
    if not explicit:
        content = "Явных источников или формализованных требований во входе не найдено. Фактические утверждения надо помечать как гипотезы."
    else:
        content = "Извлечённые опорные фрагменты:\n" + "\n".join(f"- {e['ref']}: {e['text']}" for e in explicit)
    return WorkerResult(
        worker_name="evidence",
        role="evidence",
        content=content,
        artifacts={"evidence": explicit},
        confidence=0.82 if explicit else 0.55,
    )


class WorkerPool:
    def __init__(self, provider: BaseProvider, max_workers: int = 4) -> None:
        self.provider = provider
        self.max_workers = max_workers

    def run_initial(self, contract: TaskContract) -> Dict[str, WorkerResult]:
        result: Dict[str, WorkerResult] = {}
        result["decompose"] = decompose_task(contract)
        result["generate"] = generate_candidate(contract, self.provider)
        result["critic"] = critique_candidate(contract, result["generate"].content)
        return result

    def run_deep_workers(self, contract: TaskContract) -> Dict[str, WorkerResult]:
        jobs: List[Tuple[str, object]] = [
            ("counterexample", counterexample_worker),
            ("evidence", evidence_worker),
        ]
        results: Dict[str, WorkerResult] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(fn, contract): name for name, fn in jobs}
            for future in as_completed(futures):
                name = futures[future]
                results[name] = future.result()
        return results
