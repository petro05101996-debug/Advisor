# Жёсткая проверка полного процесса v4.8.1

Дата: 2026-06-01

## Что проверено

1. Компиляция основного скрипта.
2. Regression tests: простые/средние/сложные сценарии.
3. Full SA coverage: 16 сценариев системного аналитика.
4. Rank guard: защита от подмены главной архитектуры частным слоем.
5. Product sections: Quality Gate, MVP/Production, ADR, Capacity, диаграммы.
6. Web smoke: GET `/` и POST `/generate`.
7. Ручные проверки:
   - пустой ввод;
   - hot status screen;
   - аудит проблемного Kafka consumer;
   - форматирование composite architecture;
   - корректность audit verdict при critical findings.

## Результаты автотестов

- `test_integration_architect.py` — 18/18 passed
- `test_sa_full_coverage.py` — 16/16 passed
- `test_rank_guard.py` — 3/3 passed
- `test_v48_product_sections.py` — 2/2 passed
- `test_v48_1_hard_process.py` — 3/3 passed

## Найденные проблемы v4.8

### 1. External API вызов мог падать по KeyError при неполном словаре

Через UI проблема почти не проявлялась, потому что форма подставляет defaults, но при CLI/API-вызове `Engine().generate({})` падал.

Исправлено: `generate()` теперь всегда мержит вход с нейтральными defaults.

### 2. Composite architecture для blocked-сценария печаталась как raw dict

В отчёте появлялось что-то вроде:

```text
{'layer': '0. Предпроектная проверка', ...}
```

Исправлено: слои теперь форматируются как нормальный markdown: слой, решение, компоненты, контроли, риски.

### 3. ADR для blocked-сценария мог звучать как рекомендация

В нижнем ADR-блоке было: “Использовать Решение заблокировано...”.

Исправлено: для blocked-сценария формируется только ADR-DRAFT/список вопросов, без утверждения архитектуры.

### 4. Audit verdict был слишком мягким

Проблемный Kafka consumer с critical findings мог получить GREEN/80% из-за усреднения категорий.

Исправлено: добавлены hard caps:

- есть critical findings → не выше RED/YELLOW-зоны;
- несколько high findings → не выше YELLOW;
- audit не может быть GREEN при критичных production-рисках.

### 5. Нумерация разделов после product sections была сбита

После раздела 13 снова шли разделы 4, 5, 6.

Исправлено: нумерация приведена к последовательной структуре.

## Жёсткий итог

v4.8.1 заметно лучше v4.8 именно как рабочий процесс:

- пустой ввод не ломает инструмент и честно блокируется;
- отчёт не содержит raw dict;
- ADR не утверждает заблокированное решение;
- аудит проблемной production-интеграции больше не выдаёт GREEN при critical findings;
- hard-case ranking остаётся корректным.

Оставшееся ограничение: это всё ещё детерминированный pre-architecture помощник, а не полноценный архитектор/capacity planner.
