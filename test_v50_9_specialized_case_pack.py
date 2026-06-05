#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Регрессия v5.0.9: специализированные сложные кейсы не должны сваливаться в голый общий E2E."""

from integration_architect_pro import Engine, defaults


def run(form):
    return Engine().generate(form)


def base_form():
    f = defaults()
    f.update({
        "task_type": "e2e_chain",
        "business_goal": "Сложная интеграция, требуется адресное проектирование.",
        "source_system": "Source",
        "target_system": "Target",
        "systems_matrix": "Source | Владелец данных | Team A | high | rest | blocking | 2s\nTarget | Получатель | Team B | high | kafka | async | 30s",
        "process_steps": "1 | 1 | 0 | Зафиксировать изменение | Source | rest | request | accepted | 2s | retry | manual | blocking | Team A\n1 | 2 | 1 | Передать результат | Target | kafka | event | projection | 30s | retry | dlq | non_blocking | Team B",
        "target_integration_matrix": "Source | Target | kafka | async | changed | EntityChanged | topic.entity.v1 | 5s | retry | 5 | yes | eventId | service_auth | none | Team A",
        "allowed_channels": ["rest", "kafka", "queue"],
        "change_policy": ["add_api", "add_event", "add_outbox", "add_status"],
        "current_controls": ["timeout", "retry", "dlq", "outbox", "inbox", "correlation_id", "monitoring"],
    })
    return f


def assert_contains(res, *needles):
    text = (res.get("markdown", "") + " " + str(res.get("recommended", "")) + " " + str(res.get("advanced", ""))).lower()
    for needle in needles:
        assert needle.lower() in text


def test_rest_enrichment_before_kafka_has_dedicated_block():
    f = base_form()
    f["business_situations"] = ["event_enrichment_before_publish", "source_lacks_kafka"]
    f["source_change_policy"] = "minimal_table_only"
    res = run(f)
    assert_contains(res, "REST-обогащение перед публикацией в Kafka", "Integration Publisher", "enrichmentConsistency", "FAILED/reprocess")


def test_required_contract_field_has_contract_guard():
    f = base_form()
    f["task_type"] = "contract_change"
    f["business_goal"] = "В duplicate response забыли обязательное поле по контракту."
    f["business_situations"] = ["contract_breaking_change"]
    res = run(f)
    assert_contains(res, "обязательных полей", "Contract-first", "consumer-driven contract tests")


def test_sync_chain_has_resilience_controls():
    f = base_form()
    f["result_model"] = "sync"
    f["allowed_channels"] = ["rest"]
    f["chain_depth"] = "multi_level"
    f["step_count"] = "8_plus"
    res = run(f)
    assert_contains(res, "Синхронная цепочка", "circuit breaker", "timeout budget", "retry budget")


def test_active_active_financial_write_is_specialized():
    f = base_form()
    f["business_situations"] = ["multi_region_active_active", "financial_operation"]
    f["delivery"] = "business_exactly_once"
    res = run(f)
    assert_contains(res, "Active-active финансовая запись", "single writer", "ledger", "reconciliation")


def test_cqrs_status_screen_has_read_model_block():
    f = base_form()
    f["task_type"] = "read_model"
    f["business_situations"] = ["client_status_screen", "highload_read"]
    f["operation_kind"] = "query_readonly"
    res = run(f)
    assert_contains(res, "CQRS/read model", "freshness marker", "projection lag")


def test_timezone_and_money_precision_are_explicit():
    f = base_form()
    f["business_situations"] = ["timezone_dates", "money_precision", "financial_operation"]
    res = run(f)
    assert_contains(res, "UTC", "businessDate", "currency code", "rounding policy")
