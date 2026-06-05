#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from integration_architect_pro import Engine, defaults


def hard_design_form():
    f = defaults()
    f.update({
        'project_name':'Кредитная заявка hard final check',
        'task_type':'e2e_chain',
        'business_goal':'Клиент подает кредитную заявку, получает быстрый trackingId, дальше идут антифрод, скоринг, БКИ, CRM, DWH и уведомления без блокировки core-flow.',
        'business_situations':['application_or_order_creation','client_status_screen','financial_operation','multi_step_business_process','external_api_dependency','unstable_external_provider','dwh_reporting','notification_flow','personal_data_exchange','peak_load_process','exactly_once_required'],
        'money_impact':'yes','regulatory_impact':'yes','customer_visible':'yes',
        'source_system':'Loan API','main_entity':'CreditApplication',
        'fields':'applicationId:uuid|required|unique, customerId:uuid|required|indexed|sensitive, idempotencyKey:string|required|unique, requestId:string|required|unique, amount:decimal|required, status:string|required, correlation_id:string|required, version:integer|required',
        'statuses':'ACCEPTED,FRAUD_CHECKING,SCORING,BKI_PENDING,MANUAL_REVIEW,APPROVED,REJECTED,FAILED',
        'source_of_truth':'own_db','ownership':'single',
        'load_profile':'highload','rps':'450','peak_factor':'10','payload_kb':'12','retention_days':'90','target_lag_seconds':'30',
        'response_time_expectation':'under_1s','latency_sla':'seconds','freshness_requirement':'up_to_1m',
        'consistency':'business_exactly_once','delivery':'business_exactly_once','ordering':'per_entity','replay':'rebuild',
        'orchestration':'orchestrator','chain_depth':'multi_level','step_count':'8_plus','failure_policy':'retry_compensate_manual','result_model':'tracking',
        'systems_matrix':'Loan API | entrypoint | platform | critical | rest,event | blocking | 500ms\nAntifraud | fraud check | risk | critical | kafka | non_blocking | 5s\nScoring | decision engine | risk | critical | kafka | non_blocking | 10s\nBKI | external credit bureau | partner | critical | rest,webhook | non_blocking | 30s\nCRM | customer update | sales | important | kafka | non_blocking | 1m\nNotification | status notify | product | important | kafka | non_blocking | 1m\nDWH | reporting | data | important | cdc,etl | non_blocking | 1h',
        'process_steps':'0 | 1 | root | Accept application and persist operation | Loan API | rest | request | applicationId | 500ms | yes | return same response | blocking | platform\n1 | 2 | 1 | Publish accepted event | Loan API | outbox | application | event | 1s | yes | stuck alert | non_blocking | platform\n1 | 3 | 2 | Antifraud check | Antifraud | kafka | event | fraudResult | 5s | yes | manual review | non_blocking | risk\n1 | 4 | 2 | Scoring check | Scoring | kafka | event | scoreResult | 10s | yes | manual review | non_blocking | risk\n1 | 5 | 2 | Request BKI | BKI | rest | request | bkiRequestId | 30s | yes | manual review | non_blocking | partner\n2 | 6 | 3,4,5 | Join decision | Loan API | internal | results | decision | 1s | yes | manual review | blocking | platform\n2 | 7 | 6 | Update CRM | CRM | kafka | decision | crmUpdated | 1m | yes | dlq | non_blocking | sales\n2 | 8 | 6 | Notify client | Notification | kafka | status | notification | 1m | yes | dlq | non_blocking | product\n2 | 9 | 6 | Export to DWH | DWH | cdc | data | report | 1h | yes | reconciliation | non_blocking | data',
        'existing_capabilities':['rest_api','kafka','status_model','audit','monitoring','outbox','inbox','dlq'],
        'allowed_channels':['rest','kafka','queue','cdc','etl','webhook'],
        'dwh':'near_realtime','sensitivity':'financial','auth':'service_and_user','observability':'full','manual_recovery':'yes','history':'status_audit_attempts',
        'error_matrix':'bki_timeout | BKI | non_blocking | yes | retry backoff then manual review | risk\nduplicate_callback | Loan API | non_blocking | no | inbox dedupe | platform\ndwh_gap | DWH | non_blocking | yes | reconciliation | data'
    })
    return f


def test_readiness_is_consistent_in_summary_and_adr():
    res = Engine().generate(hard_design_form())
    score = res['readiness']['score']
    assert f'**Готовность требований:** {score}%' in res['markdown']
    assert f'Готовность требований: {score}%.' in res['markdown']


def test_ddl_has_no_duplicate_system_fields():
    res = Engine().generate(hard_design_form())
    ddl = res['db']['ddl']
    first_table = ddl.split(');', 1)[0]
    assert first_table.count('status text not null') == 1
    assert first_table.count('version integer not null default 1') == 1
    assert first_table.count('correlation_id text') == 1


def test_capacity_has_numeric_minimum_and_range():
    res = Engine().generate(hard_design_form())
    cap = res['advanced']['capacity']
    assert isinstance(cap['recommended_partitions'], int)
    assert cap['recommended_partitions'] >= 6
    assert '–' in cap['recommended_partitions_range']
    assert 'Это не sizing' in ' '.join(cap['notes'])


def test_context_diagram_branches_from_process_manager():
    res = Engine().generate(hard_design_form())
    diagram = res['advanced']['extra_diagrams']['context']
    assert 'PM[Process Manager / State Machine]' in diagram
    assert 'PM -. async/non-blocking .->' in diagram
    assert 'Status Read Model' in diagram


def test_quality_gate_does_not_ask_missing_idempotency_when_present():
    res = Engine().generate(hard_design_form())
    questions = '\n'.join(res['advanced']['quality_gate']['critical_questions'])
    assert 'Какой idempotency key' not in questions
    assert 'TTL, scope' in questions


def test_audit_subscores_are_capped_by_critical_findings():
    f = defaults()
    f.update({
        'task_type':'audit_existing_solution','project_name':'Аудит плохой production-интеграции',
        'load_profile':'highload','rps':'500','peak_factor':'5','consistency':'business_exactly_once','dwh':'near_realtime','sensitivity':'financial','audit_depth':'deep',
        'current_systems_matrix':'Loan API | Loan API | service | platform | critical | yes | own_db | application\nBKI | BKI | external | partner | critical | no | external | credit_report\nKafka | Kafka | broker | platform | critical | yes | none | events\nCRM | CRM | service | sales | important | yes | external | customer\nDWH | DWH | analytics | data | important | yes | report | report',
        'current_integration_matrix':'Client | Loan API | rest | sync | yes | request | 1s | no | 0 | no | no | user | prod\nLoan API | BKI | rest | sync | no | report | 30s | yes | 3 | no | no | service | prod\nLoan API | Kafka | kafka | async | no | events | 1s | yes | 3 | no | no | service | prod\nKafka | CRM | kafka | async | no | decision | 1m | yes | 3 | no | no | service | prod\nLoan API | DWH | db | sync | no | tables | 1h | no | 0 | no | no | dbuser | prod',
        'current_process_steps':'1 | root | 1 | Accept request | Loan API | BKI | rest | yes | bki result | timeout | retry | no\n2 | 1 | 2 | Publish event | Loan API | Kafka | kafka | no | event | lost | retry | no\n3 | 2 | 3 | Update CRM | CRM | DB | kafka | no | update | error | log only | no',
        'current_error_matrix':'bki_timeout | Loan API | technical | yes | no | retry | yes | platform | no\nevent_lost | Kafka | technical | no | yes | manual sql | no | platform | no\ncrm_error | CRM | technical | no | yes | log only | no | sales | no',
        'current_problem_matrix':'lost events | Kafka | daily | high | lost decisions\nduplicates | CRM | daily | high | duplicate updates\nstuck statuses | Loan API | daily | high | manual support',
        'current_controls':['monitoring']
    })
    res = Engine().generate(f)
    scores = res['ctx']['scores'] if 'scores' in res.get('ctx',{}) else None
    # audit result does not expose ctx; parse scores indirectly from markdown
    md = res['markdown']
    assert 'Вердикт:** RED' in md
    assert 'Надёжность: 55/100' in md or 'Надёжность: 60/100' in md
    assert 'Согласованность данных: 50/100' in md or 'Согласованность данных: 60/100' in md
    assert 'Наблюдаемость: 60/100' in md


def enrichment_single_kafka_form():
    f = defaults()
    f.update({
        'project_name':'Договоры: обогащённое событие в Kafka',
        'task_type':'add_to_existing',
        'business_goal':'Сервис договоров хранит договоры и их обновления. Обновления нужно передавать другому сервису через Kafka, но перед отправкой событие нужно дообогатить данными из отдельного REST-сервиса. Kafka topic только один, Kafka-инфраструктуры в source-сервисе нет.',
        'business_situations':['data_synchronization','data_enrichment','external_api_dependency','one_source_many_consumers'],
        'source_system':'Contract Service',
        'main_entity':'Contract',
        'fields':'contractId:uuid|required|unique|indexed, clientId:uuid|required|indexed|sensitive, status:string|required, idempotencyKey:string|unique, version:integer|required',
        'systems_matrix':'Contract Service | source of truth for contracts | Contracts Team | critical | rest,outbox | blocking | 500ms\nEnrichment Service | owns additional attributes | Data Team | important | rest | non_blocking | 1s\nTarget Service | consumes contract updates | Target Team | important | kafka | non_blocking | 30s',
        'process_steps':'0 | 1 | root | Update contract and increment version | Contract Service | rest | command | contractVersion | 500ms | yes | reject/manual | blocking | Contracts Team\n1 | 2 | 1 | Save pending outbox event | Contract Service | outbox | contractId,version | sourceEventId | 100ms | yes | stuck alert | non_blocking | Contracts Team\n1 | 3 | 2 | Enrich event payload | Enrichment Service | rest | contractId,version | enrichment data | 1s | yes | retry/failed/manual reprocess | non_blocking | Data Team\n1 | 4 | 3 | Publish final event to Kafka | Integration Publisher | kafka | enriched payload | ContractUpdated | 1s | yes | DLQ/stuck alert | non_blocking | Platform Team',
        'statuses':'UPDATED, OUTBOX_PENDING, ENRICHING, PUBLISHED, ENRICHMENT_FAILED',
        'final_statuses':'PUBLISHED, ENRICHMENT_FAILED',
        'source_of_truth':'own_db',
        'ownership':'field_level',
        'event_payload_intent':'enriched_event',
        'enrichment_required':'required',
        'enrichment_owner_service':'Enrichment Service',
        'enrichment_consistency':'current_at_publish',
        'allowed_channels':['rest','kafka','queue'],
        'kafka_topology':'single_topic_only',
        'source_has_kafka_infra':'no',
        'enrichment_channel':'rest',
        'existing_state':'production',
        'change_policy':['add_outbox','add_event','add_status'],
        'existing_capabilities':['rest_api','status_model','audit','monitoring'],
        'load_profile':'medium','rps':'50','peak_factor':'2','latency_sla':'async_minutes','result_model':'not_needed',
        'delivery':'at_least_once','ordering':'per_entity','replay':'short','history':'status_audit_attempts',
        'dwh':'no','manual_recovery':'yes','observability':'full','sensitivity':'pii',
        'error_matrix':'enrichment_timeout | Integration Publisher | non_blocking | yes | FAILED + manual reprocess | Data Team\nkafka_publish_error | Integration Publisher | non_blocking | yes | stuck alert | Platform Team'
    })
    return f


def test_single_kafka_rest_enrichment_selects_enrichment_publisher_variant():
    res = Engine().generate(enrichment_single_kafka_form())
    assert res['recommended']['name'] == 'Outbox + REST Enrichment Publisher'
    assert 'integration_publisher' in res['recommended']['pattern_ids']
    assert 'outbox' in res['recommended']['pattern_ids']
    assert 'kafka' in res['recommended']['pattern_ids']
    md = res['markdown']
    assert 'source-сервис владеет фактом изменения' in md
    assert 'raw-событие отдельно не публикуется' in md
    assert 'Integration Publisher / обогащение события' in md


def test_enrichment_pipeline_adds_tables_contracts_and_controls():
    res = Engine().generate(enrichment_single_kafka_form())
    table_names = {t['name'] for t in res['db']['tables']}
    assert 'outbox_events' in table_names
    assert 'event_enrichment_attempts' in table_names
    ddl = res['db']['ddl']
    assert 'enrichment_status' in ddl
    assert 'source_event_id' in ddl
    assert 'event_enrichment_attempts' in ddl
    enrichment_contract = '\n'.join(res['contracts']['enrichment'])
    assert 'REST enrichment contract' in enrichment_contract
    assert 'AS_OF_CHANGE' in enrichment_contract
    event_contract = '\n'.join(res['contracts']['events'])
    assert 'sourceEventId/outboxEventId' in event_contract
    assert 'publish only final enriched payload' in event_contract


def test_enrichment_antipatterns_catch_ownership_and_consistency():
    f = enrichment_single_kafka_form()
    f['enrichment_consistency'] = 'unknown'
    res = Engine().generate(f)
    anti_ids = {a['id'] for a in res['anti_patterns']}
    assert 'event_ownership_vs_kafka_infra' in anti_ids
    assert 'enrichment_consistency_not_defined' in anti_ids
    questions = '\n'.join(res['advanced']['quality_gate']['critical_questions'])
    assert 'business owner события' in questions
    assert 'момент изменения сущности' in questions


def test_enrichment_event_diagram_contains_rest_before_single_kafka():
    res = Engine().generate(enrichment_single_kafka_form())
    diagram = res['advanced']['extra_diagrams']['event_flow']
    assert 'Integration Publisher' in diagram
    assert 'Enrichment REST Service' in diagram
    assert 'Kafka single topic' in diagram
    assert 'publish final enriched event' in diagram


def test_raw_and_enriched_topics_allowed_selects_two_stage_event_pipeline():
    f = enrichment_single_kafka_form()
    f['kafka_topology'] = 'raw_enriched_topics'
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Raw + Enriched Event Pipeline'
    md = res['markdown']
    assert 'raw domain fact' in md or 'raw-факт' in md
    assert 'enriched snapshot' in md or 'enriched-событие' in md


def test_required_enrichment_flags_no_outbox_or_cdc_allowed():
    f = enrichment_single_kafka_form()
    f['change_policy'] = ['add_event']
    f['existing_capabilities'] = ['rest_api','status_model']
    res = Engine().generate(f)
    anti_ids = {a['id'] for a in res['anti_patterns']}
    assert 'enrichment_requires_change_but_outbox_not_allowed' in anti_ids
