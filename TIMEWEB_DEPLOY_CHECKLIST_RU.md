# Timeweb deploy checklist

## Перед деплоем

- Dockerfile лежит в корне проекта.
- Приложение слушает `HOST=0.0.0.0`.
- Порт берётся из переменной `PORT`, по умолчанию `8110`.
- В Dockerfile указан `EXPOSE 8110`.
- Healthcheck ходит на `/`.
- Для production-хранения SQLite/generated_reports лучше заменить на внешнее хранилище, если нужно сохранять историю между redeploy.

## Локальная проверка

```bash
python -m py_compile integration_architect_pro.py
pytest -q
python integration_architect_pro.py
```

Открыть:

```text
http://127.0.0.1:8110/
```
