from integration_architect_pro import form_page


def test_advanced_mode_is_still_beginner_friendly():
    html = form_page()
    assert "Расширенный режим: тоже пошагово" in html
    assert "Расширенный режим без усложнения" in html
    assert "Это не экзамен по архитектуре" in html
    assert "цель → системы → шаги → ошибки" in html
    assert "section-guide" in html
    assert "Смысл блока" in html
    assert "Участники" in html
    assert "Процесс как история" in html
    assert "Надёжность" in html


def test_complex_matrices_have_plain_language_tips():
    html = form_page()
    assert "Подсказка: Формат: Система | роль | владелец" in html
    assert "Подсказка: Формат: level | order | parent" in html
    assert "Подсказка: Формат: ошибка | где" in html
    assert "Подсказка: Опишите реальные ограничения" in html
    assert "Вернуть простой мастер" in html
