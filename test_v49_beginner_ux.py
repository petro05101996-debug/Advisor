from integration_architect_pro import form_page, Engine, defaults, result_page


def test_beginner_ui_is_simple_by_default():
    html = form_page()
    assert "Простой мастер по умолчанию" in html
    assert "Простой мастер: без архитектурных терминов" in html
    assert "body:not(.power-mode) details.section" in html
    assert "2. Сформировать отчёт" in html
    assert "Расширенный режим: тоже пошагово" in html


def test_result_page_has_beginner_summary():
    f = defaults()
    f.update({
        "project_name": "UX smoke simple integration",
        "business_goal": "Передать заявку из сайта в CRM",
        "business_situations": ["application_or_order_creation", "external_api_dependency"],
        "systems_matrix": "Web/API | intake | Team | important | rest | blocking | 2s\nCRM | customer card | CRM Team | important | rest | blocking | 5s",
        "process_steps": "0 | 1 | root | Принять заявку | Web/API | rest | request | id | 2s | no | reject | blocking | Team\n1 | 2 | 1 | Создать карточку | CRM | rest | data | crmId | 5s | yes | manual | blocking | CRM Team",
        "fields": "id:uuid|required|unique, status:string|required",
        "load_profile": "low",
        "rps": "10",
    })
    res = Engine().generate(f)
    html = result_page(res, "rid", "report.md")
    assert "Итог простыми словами" in html
    assert "Выжимка для новичка" in html
    assert "Показать полный технический отчёт" in html
    assert "## 0. Финальное решение в 5 строк для новичка" in res["markdown"]
