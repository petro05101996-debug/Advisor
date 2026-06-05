from integration_architect_pro import form_page


def test_e2e_builder_uses_choices_not_free_text_for_beginner_flow():
    html = form_page()
    assert "Интеграционный инструктор v4.9.8" in html
    assert "Выбирайте ответы из готовых вариантов" in html
    assert "Что является главным объектом?" in html
    assert "Сколько систем участвует?" in html
    assert "Где источник правды?" in html
    assert "Куда нужен результат?" in html
    assert "Нужно обогащение данными?" in html
    assert "Что разрешено менять?" in html
    assert "Ограничения проекта" in html
    assert "Какие ошибки обязательно закрыть?" in html
    assert "Что надо получить на выходе?" in html
    assert "Системы через запятую" not in html
    assert "Название задачи" not in html


def test_choice_builder_generates_e2e_fields_in_javascript():
    html = form_page()
    assert "namesByChoices" in html
    assert "checkedVals('simple_constraints')" in html
    assert "setField('systems_matrix', basicSystems(systems, scenario))" in html
    assert "setField('process_steps', basicSteps(systems, scenario))" in html
    assert "setField('error_matrix', errRows.length ? errRows.join" in html
    assert "setField('enrichment_required'" in html
    assert "setField('kafka_topology'" in html
    assert "setField('compromise_comment'" in html
