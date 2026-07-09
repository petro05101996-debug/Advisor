# AUDIT REPORT — CogProxy DQE User Core v0.3

## Вердикт

Ядро рабочее. v0.3 уже полезнее для пользователя, потому что добавлен прикладной сценарий: анализ бага по логам/stacktrace/коду/документации.

## Что стало полезно пользователю

Пользователь может прийти с минимальными данными:

```text
- лог
- stacktrace
- папка проекта
- документация, если есть
```

И получить не общий ответ, а артефакты:

```text
- наиболее вероятная причина
- цепочка доказательств log → stacktrace → code/docs
- подозрительные файлы и строки
- snippets кода вокруг строки падения
- гипотезы root cause с confidence
- шаги подтверждения
- минимальный fix
- regression tests
- prompt для внешней модели
```

## Что важно честно понимать

Без реальной LLM модуль `bug_analysis` работает как deterministic evidence collector + heuristic root-cause assistant. Он хорошо находит простые классы проблем: `None/null`, `KeyError`, `IndexError`, parsing errors, connection/timeout, DB constraint. Но он не гарантирует причину в произвольном сложном distributed bug.

С внешней CLI-моделью ценность выше: DQE собирает и сжимает контекст проекта, чтобы модель не читала всё вслепую и не отвечала общими советами.

## Оценка после v0.3

| Критерий | Оценка |
|---|---:|
| Запускаемость ядра | 8/10 |
| CLI / packaging | 8/10 |
| Пользовательская полезность offline | 7/10 |
| Bug analysis usefulness | 7/10 |
| Честность receipt | 7/10 |
| Подготовка контекста для модели | 7/10 |
| Реальное доказательство LLM uplift | 2/10 |
| Production readiness | 3/10 |

## Следующий шаг

Нужно сделать project-aware iterative debugging:

```text
1. первый проход: stacktrace → suspect snippets
2. модель даёт гипотезу
3. CogProxy ищет дополнительные файлы по гипотезе
4. модель уточняет root cause
5. CogProxy предлагает fix + regression test
6. если возможно — запускает тесты/команды проекта
```

Это превратит модуль из хорошего evidence collector в настоящий debugging copilot.


## v0.3.1 integrity note
A later integrity audit fixed CLI `--json` large-output handling and confirmed no v0.2 files were removed. See `INTEGRITY_AUDIT_V0_3_1.md`.
