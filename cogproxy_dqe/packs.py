from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DomainPack:
    name: str
    description: str
    required_sections: List[str]
    quality_dimensions: List[str]
    verifier_names: List[str]
    default_success_criteria: List[str]
    risk_keywords: List[str] = field(default_factory=list)
    section_guidance: Dict[str, str] = field(default_factory=dict)
    output_type: str = "structured_answer"


class PackRegistry:
    def __init__(self) -> None:
        self._packs: Dict[str, DomainPack] = {}
        self._register_defaults()

    def register(self, pack: DomainPack) -> None:
        self._packs[pack.name] = pack

    def get(self, name: Optional[str]) -> DomainPack:
        if not name:
            return self._packs["universal"]
        normalized = name.strip().lower().replace("-", "_")
        if normalized not in self._packs:
            available = ", ".join(sorted(self._packs))
            raise ValueError(f"Unknown pack '{name}'. Available packs: {available}")
        return self._packs[normalized]

    def names(self) -> List[str]:
        return sorted(self._packs)

    def _register_defaults(self) -> None:
        self.register(DomainPack(
            name="universal",
            description="General-purpose quality pack for complex answers.",
            required_sections=[
                "Цель",
                "Ключевые выводы",
                "Решение",
                "Риски",
                "Следующие шаги",
            ],
            quality_dimensions=[
                "correctness",
                "completeness",
                "actionability",
                "risk_awareness",
                "clarity",
            ],
            verifier_names=[
                "required_sections",
                "coverage",
                "contradiction",
                "actionability",
                "risk_coverage",
            ],
            default_success_criteria=[
                "ответ закрывает цель пользователя",
                "есть конкретные шаги реализации",
                "есть явные риски и ограничения",
                "нет внутренних противоречий",
            ],
            risk_keywords=["риск", "ограничение", "компромисс", "ошибка"],
            section_guidance={
                "Цель": "Зафиксировать, какую задачу решаем и какой результат считаем полезным.",
                "Ключевые выводы": "Сжато назвать главное без воды.",
                "Решение": "Дать рабочую структуру решения.",
                "Риски": "Показать, где подход может сломаться.",
                "Следующие шаги": "Дать проверяемый план внедрения.",
            },
        ))
        self.register(DomainPack(
            name="system_design",
            description="System design quality pack focused on requirements-first architecture.",
            required_sections=[
                "Цель и границы",
                "Участники и сценарии",
                "Инварианты и SLA",
                "Данные и состояния",
                "Архитектура",
                "Критические потоки",
                "Отказы и риски",
                "План реализации",
            ],
            quality_dimensions=[
                "requirements_coverage",
                "critical_invariant_detection",
                "sla_reasoning",
                "failure_modes",
                "minimal_sufficient_architecture",
                "operability",
            ],
            verifier_names=[
                "required_sections",
                "coverage",
                "contradiction",
                "actionability",
                "risk_coverage",
            ],
            default_success_criteria=[
                "описаны границы и участники",
                "выделены главные инварианты и SLA",
                "выделены критические потоки",
                "архитектура минимально достаточна, а не избыточна",
                "описаны отказы и способы контроля",
            ],
            risk_keywords=["SLA", "инвариант", "отказ", "идемпотент", "консистент", "DLQ", "retry", "таймаут"],
            section_guidance={
                "Цель и границы": "Что проектируем, что не входит в решение.",
                "Участники и сценарии": "Кто вызывает систему и какие основные сценарии нужны.",
                "Инварианты и SLA": "Что нельзя нарушить и какие целевые ограничения важны.",
                "Данные и состояния": "Сущности, статусы, источник истины, жизненный цикл.",
                "Архитектура": "Компоненты, связи, синхронность/асинхронность, хранение.",
                "Критические потоки": "Пути, где ошибка дорого стоит; их изоляция.",
                "Отказы и риски": "Сбои, гонки, дубли, задержки, деградация.",
                "План реализации": "Минимальный инкремент, затем усиление.",
            },
            output_type="architecture_proposal",
        ))
        self.register(DomainPack(
            name="requirements_qa",
            description="Requirements and QA pack for documentation analysis and test generation.",
            required_sections=[
                "Цель проверки",
                "Нормализованные требования",
                "Сценарии",
                "Тест-кейсы",
                "Негативные проверки",
                "Покрытие требований",
                "Риски и вопросы",
                "Отчёт",
            ],
            quality_dimensions=[
                "requirements_traceability",
                "positive_negative_coverage",
                "state_transition_coverage",
                "edge_cases",
                "testability",
            ],
            verifier_names=[
                "required_sections",
                "coverage",
                "contradiction",
                "actionability",
                "risk_coverage",
            ],
            default_success_criteria=[
                "каждое требование имеет проверку",
                "есть позитивные и негативные сценарии",
                "есть проверки переходов состояний",
                "есть трассировка требование → тест",
                "неясности вынесены в вопросы",
            ],
            risk_keywords=["требование", "сценарий", "статус", "ошибка", "негатив", "покрытие", "тест"],
            section_guidance={
                "Цель проверки": "Что именно проверяем в документации или сервисе.",
                "Нормализованные требования": "Разложить исходный текст на атомарные требования.",
                "Сценарии": "Позитивные, альтернативные и ошибочные ветки.",
                "Тест-кейсы": "Проверяемые тесты с предусловиями и ожидаемым результатом.",
                "Негативные проверки": "Ошибки, лимиты, неверные статусы, дубли, таймауты.",
                "Покрытие требований": "Связь между требованиями и тестами.",
                "Риски и вопросы": "Неясности, противоречия и непроверяемые места.",
                "Отчёт": "Краткое резюме готовности и пробелов.",
            },
            output_type="qa_report",
        ))
        self.register(DomainPack(
            name="research_analysis",
            description="Research and strategy analysis pack with evidence, counterarguments and implementation plan.",
            required_sections=[
                "Тезис",
                "Что подтверждается",
                "Что не доказано",
                "Архитектура решения",
                "Критика",
                "MVP",
                "Метрики проверки",
                "Вывод",
            ],
            quality_dimensions=[
                "evidence_support",
                "counterarguments",
                "implementation_feasibility",
                "non_cherrypicking",
                "evaluation_plan",
            ],
            verifier_names=[
                "required_sections",
                "coverage",
                "contradiction",
                "actionability",
                "risk_coverage",
                "unsupported_claims",
            ],
            default_success_criteria=[
                "отделены подтверждённые факты от гипотез",
                "есть критика и контраргументы",
                "есть реалистичный MVP",
                "есть метрики проверки эффективности",
                "нет неподдержанных сильных утверждений",
            ],
            risk_keywords=["гипотеза", "доказано", "метрика", "эксперимент", "контраргумент", "MVP", "бенчмарк"],
            section_guidance={
                "Тезис": "Сформулировать главную проверяемую идею.",
                "Что подтверждается": "Что можно считать обоснованным по текущей логике или источникам.",
                "Что не доказано": "Где нет строгого доказательства и нужен эксперимент.",
                "Архитектура решения": "Компоненты, поток данных, роли проверок.",
                "Критика": "Сильные возражения, где идея может не сработать.",
                "MVP": "Минимальная реализация, которую можно проверить.",
                "Метрики проверки": "Как измерить прирост качества, цену и задержку.",
                "Вывод": "Решение: стоит/не стоит делать и почему.",
            },
            output_type="research_strategy_report",
        ))

        self.register(DomainPack(
            name="bug_analysis",
            description="Bug/root-cause analysis pack for logs, stacktraces, code and documentation.",
            required_sections=[
                "Итог",
                "Что известно из лога и stacktrace",
                "Цепочка доказательств",
                "Гипотезы root cause",
                "Snippets кода и документации",
                "Взаимодействие с моделью",
                "Что ещё нужно от клиента",
            ],
            quality_dimensions=[
                "root_cause_hypothesis",
                "stacktrace_to_code_traceability",
                "evidence_grounding",
                "verification_steps",
                "minimal_fix_plan",
                "regression_tests",
            ],
            verifier_names=[
                "required_sections",
                "coverage",
                "actionability",
                "risk_coverage",
                "unsupported_claims",
            ],
            default_success_criteria=[
                "названа наиболее вероятная причина",
                "есть связь log stacktrace code docs",
                "есть проверяемые шаги подтверждения",
                "есть минимальный fix",
                "есть regression tests",
                "отделена гипотеза от доказанного",
            ],
            risk_keywords=["stacktrace", "traceback", "exception", "error", "root cause", "лог", "баг", "ошибка", "null", "None"],
            section_guidance={
                "Итог": "Сразу назвать наиболее вероятную причину и уровень уверенности.",
                "Что известно из лога и stacktrace": "Вытащить exception, message, frames, сервис, correlationId/requestId, если есть.",
                "Цепочка доказательств": "Связать log → stacktrace → код → документацию, не фантазировать без evidence.",
                "Гипотезы root cause": "Дать ранжированные гипотезы с confidence и доказательствами.",
                "Snippets кода и документации": "Показать релевантные фрагменты файлов вокруг строки падения.",
                "Взаимодействие с моделью": "Зафиксировать, была ли вызвана модель и что она добавила.",
                "Что ещё нужно от клиента": "Запросить минимальные данные для подтверждения причины.",
            },
            output_type="bug_root_cause_report",
        ))


def default_registry() -> PackRegistry:
    return PackRegistry()
