#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полное пользовательское тестирование инструмента глазами системного аналитика."""
from integration_architect_pro import Engine, defaults


def form(**kw):
    f = defaults()
    f.update({
        'project_name': kw.pop('project_name', 'SA test case'),
        'business_goal': kw.pop('business_goal', 'Проверочный бизнес-сценарий.'),
        'source_system': kw.pop('source_system', 'Source'),
        'main_entity': kw.pop('main_entity', 'Entity'),
        'fields': kw.pop('fields', 'id:uuid|required|unique, status:string|required, idempotencyKey:string|unique'),
        'source_of_truth': kw.pop('source_of_truth', 'own_db'),
        'ownership': kw.pop('ownership', 'single'),
        'retention': kw.pop('retention', '1_year'),
        'allowed_channels': kw.pop('allowed_channels', ['rest','kafka','queue','webhook','cdc','etl','sftp','soap','graphql']),
        'forbidden_channels': kw.pop('forbidden_channels', ['direct_db_write']),
    })
    f.update(kw)
    return f


def run_case(name, f, expect_name=None, expect_patterns=(), expect_business=(), min_readiness=None, blocked=None, expect_conflict=False):
    res = Engine().generate(f)
    rec = res['recommended']['name']
    pids = set(res['recommended'].get('pattern_ids', []))
    active = set(res['ctx'].get('business', {}).get('active_scenarios', []))
    conflicts = res['ctx'].get('business', {}).get('conflicts', [])
    if expect_name:
        assert rec == expect_name, f'{name}: expected {expect_name}, got {rec}'
    for p in expect_patterns:
        assert p in pids, f'{name}: missing pattern {p}; got {sorted(pids)}; rec={rec}'
    for b in expect_business:
        assert b in active, f'{name}: missing business scenario {b}; got {sorted(active)}'
    if min_readiness is not None:
        assert res['readiness']['score'] >= min_readiness, f'{name}: readiness {res["readiness"]}'
    if blocked is not None:
        assert bool(res['recommended'].get('blocked')) is blocked, f'{name}: blocked mismatch; rec={res["recommended"]}'
    if expect_conflict:
        assert conflicts, f'{name}: expected business conflict, got none'
    print(f'OK {name}: {rec}, score={res["recommended"].get("score")}, readiness={res["readiness"]["score"]}')
    return res


def main():
    # 1. Простая REST-интеграция. Специально с заголовками таблиц — UX-кейс пользователя.
    run_case('01_simple_rest_with_headers', form(
        task_type='new_from_scratch', business_situations=['application_or_order_creation'],
        load_profile='low', rps='10', peak_factor='1', latency_sla='seconds', consistency='strong', orchestration='single', chain_depth='single_level', step_count='2_3', result_model='sync',
        systems_matrix='name | role | owner | criticality | channel | blocking | sla\nWeb/API | приём заявки | Product | important | rest | blocking | 1s\nCRM | карточка | CRM | important | rest | blocking | 3s',
        process_steps='level | order | parent | step | system | channel | input | output | timeout | retry | compensation | blocking | owner\n0 | 1 | root | Принять заявку | Web/API | rest | request | applicationId | 1s | no | reject | blocking | Product\n1 | 2 | 1 | Создать карточку CRM | CRM | rest | applicationId | crmId | 3s | yes | CRM_ERROR | blocking | CRM',
        error_matrix='error | where | blocking | retry | after_retry | owner\ncrm_timeout | CRM | blocking | yes | CRM_ERROR | CRM'
    ), expect_name='Basic API + DB', expect_patterns=['rest','postgres'], min_readiness=70)

    # 2. Клиентский hot status/read path.
    run_case('02_hot_client_status_cache', form(
        task_type='new_from_scratch', business_situations=['client_status_screen','highload_read','external_api_dependency'], customer_visible='yes', read_frequency='very_high', change_frequency='daily', response_time_expectation='under_300ms', freshness_requirement='up_to_1m', business_priority='speed', unavailable_behavior='show_stale', external_dependency_stability='limited', load_profile='highload', rps='3000', peak_factor='10', latency_sla='subsecond', consistency='eventual_ok', orchestration='single', chain_depth='single_level', step_count='2_3', result_model='sync',
        systems_matrix='Status API | экран статуса | App | critical | rest | blocking | 300ms\nSource Status | источник | Core | critical | rest,event | blocking | 3s',
        process_steps='0 | 1 | root | Прочитать read model | Status API | rest | applicationId | status,lastUpdated | 300ms | no | stale | blocking | App\n1 | 2 | 1 | Обновить read model | Source Status | event | status | projection | 1m | yes | retry | non_blocking | Core'
    ), expect_name='Fast Read / Cached Read Model', expect_patterns=['cache','read_model_business'], expect_business=['client_status_screen','highload_read'])

    # 3. Деньги/лимит: практически ровно один раз.
    run_case('03_financial_operation', form(
        task_type='external_partner', business_situations=['financial_operation','exactly_once_required','regulatory_process','external_api_dependency'], money_impact='yes', regulatory_impact='yes', customer_visible='yes', freshness_requirement='strict', stale_data_impact='financial', unavailable_behavior='manual_review', consistency='business_exactly_once', delivery='business_exactly_once', ordering='per_entity', replay='audit', orchestration='orchestrator', chain_depth='multi_level', step_count='4_7', failure_policy='retry_compensate_manual', result_model='tracking',
        systems_matrix='Payment API | операция | Payments | critical | rest | blocking | 1s\nCore Banking | списание | ABS | critical | rest | blocking | 3s\nPartner | подтверждение | Partner | critical | webhook | non_blocking | 30s',
        process_steps='0 | 1 | root | Создать operation | Payment API | rest | request | operationId | 1s | no | reject | blocking | Payments\n1 | 2 | 1 | Списать сумму | Core Banking | rest | operationId | debitStatus | 3s | yes | compensate | blocking | ABS\n2 | 3 | 2 | Получить callback | Partner | webhook | event | finalStatus | 30s | yes | manual | non_blocking | Partner'
    ), expect_name='Financial Operation State Machine', expect_patterns=['outbox','inbox','saga'], expect_business=['financial_operation','exactly_once_required'])

    # 4. Сложная кредитная E2E цепочка: scoring/BKI/anti-fraud/CRM/DWH/notifications/status.
    run_case('04_complex_loan_e2e_fanout_fanin', form(
        project_name='Кредитная E2E цепочка', task_type='e2e_chain', business_situations=['application_or_order_creation','multi_step_business_process','client_status_screen','financial_operation','external_api_dependency','dwh_reporting','notification_flow','personal_data_exchange','regulatory_process'], customer_visible='yes', money_impact='yes', regulatory_impact='yes', load_profile='highload', rps='700', peak_factor='10', latency_sla='async_minutes', consistency='business_exactly_once', delivery='business_exactly_once', ordering='per_entity', replay='rebuild', orchestration='orchestrator', chain_depth='fanout_fanin', step_count='8_plus', failure_policy='retry_compensate_manual', result_model='tracking', dwh='regulatory', sensitivity='pii', observability='regulated', testing='regulated',
        systems_matrix='API | command | Product | critical | rest | blocking | 1s\nBKI | credit report | External | critical | rest | blocking | 10s\nScoring | decision | Risk | critical | queue | blocking | 30s\nAntifraud | fraud check | Risk | critical | queue | blocking | 10s\nCRM | customer card | CRM | important | event | non_blocking | 1m\nNotify | notifications | Comm | non_critical | event | non_blocking | 1m\nDWH | regulatory | Data | critical | cdc,etl | non_blocking | 1d',
        process_steps='0 | 1 | root | Принять заявку | API | rest | request | applicationId | 1s | no | reject | blocking | Product\n1 | 2 | 1 | Запросить БКИ | BKI | rest | applicationId | report | 10s | yes | manual | blocking | Risk\n1 | 3 | 1 | Антифрод | Antifraud | queue | applicationId | fraudResult | 10s | yes | manual | blocking | Risk\n2 | 4 | 2,3 | Скоринг | Scoring | queue | report,fraud | decision | 30s | yes | manual | blocking | Risk\n3 | 5 | 4 | Опубликовать статус | API | kafka | status | event | 1s | yes | outbox | blocking | Platform\n4 | 6 | 5 | CRM | CRM | event | status | crmStatus | 1m | yes | dlq | non_blocking | CRM\n4 | 7 | 5 | Notify | Notify | event | status | push | 1m | yes | dlq | non_blocking | Comm\n4 | 8 | 5 | DWH | DWH | cdc/etl | snapshot | report | 1d | yes | reconciliation | non_blocking | Data\n5 | 9 | 6,7,8 | Join status | API | db | branches | finalStatus | 1m | yes | manual | blocking | Product'
    ), expect_name='Fan-out/Fan-in Orchestrated Process', expect_patterns=['saga','outbox','cqrs'], expect_business=['multi_step_business_process','client_status_screen','dwh_reporting'], min_readiness=70)

    # 5. Event choreography: один источник — много независимых потребителей.
    run_case('05_event_choreography_many_consumers', form(
        task_type='event_domain', business_situations=['one_source_many_consumers','notification_flow','dwh_reporting'], load_profile='highload', rps='1200', peak_factor='5', consistency='eventual_ok', delivery='at_least_once', ordering='per_entity', replay='long', orchestration='choreography', chain_depth='fanout', step_count='4_7', result_model='not_needed',
        systems_matrix='Order Service | source | Orders | critical | kafka | blocking | 1s\nBilling | consumer | Pay | critical | event | non_blocking | 30s\nDWH | analytics | Data | important | event | non_blocking | 15m\nNotify | comm | Comm | non_critical | event | non_blocking | 1m',
        process_steps='0 | 1 | root | Publish OrderCreated | Order Service | kafka | order | event | 1s | yes | outbox | blocking | Orders\n1 | 2 | 1 | Billing consumes | Billing | event | event | paymentStatus | 30s | yes | dlq | non_blocking | Pay\n1 | 3 | 1 | DWH consumes | DWH | event | event | dwhRow | 15m | yes | replay | non_blocking | Data\n1 | 4 | 1 | Notify consumes | Notify | event | event | push | 1m | yes | dlq | non_blocking | Comm'
    ), expect_name='Event Choreography', expect_patterns=['kafka','outbox','inbox'])

    # 6. Webhook/callback.
    run_case('06_webhook_callback', form(
        task_type='external_partner', business_situations=['webhook_callback','external_api_dependency','exactly_once_required'], external_dependency_stability='unstable', unavailable_behavior='queue_for_later', delivery='business_exactly_once', ordering='per_entity', result_model='callback', orchestration='single', chain_depth='single_level', step_count='1',
        systems_matrix='Partner | callback source | External | critical | webhook | non_blocking | 5s\nWebhook Gateway | intake | Platform | critical | webhook,queue | blocking | 1s',
        process_steps='0 | 1 | root | Принять callback в Inbox | Webhook Gateway | webhook | event | ack | 1s | yes | inbox retry | non_blocking | Platform',
        fields='external_event_id:string|required|unique, operationId:string|required|indexed, payloadHash:string|required'
    ), expect_name='Webhook Intake + Inbox Processing', expect_patterns=['webhook','inbox','queue'])

    # 7. DWH/regulatory batch.
    run_case('07_regulatory_dwh_batch', form(
        task_type='dwh_analytics', business_situations=['dwh_reporting','batch_processing','regulatory_process','personal_data_exchange'], regulatory_impact='yes', sensitivity='pii', dwh='regulatory', load_profile='medium', latency_sla='daily', freshness_requirement='daily', consistency='eventual_ok', delivery='at_least_once', replay='rebuild', orchestration='single', chain_depth='single_level', step_count='2_3', result_model='report', source_of_truth='external', ownership='external', data_volume='very_large', retention='5_years',
        systems_matrix='Core DB | operations | Core | critical | cdc | non_blocking | daily\nDWH | reporting | Data | critical | etl | non_blocking | daily',
        process_steps='0 | 1 | root | CDC to staging | Core DB | cdc | changes | staging | daily | yes | retry offset | non_blocking | Data\n1 | 2 | 1 | Build mart | DWH | etl | staging | report | daily | yes | reconciliation | non_blocking | Data'
    ), expect_name='Data Pipeline / DWH', expect_patterns=['cdc','etl'], expect_business=['dwh_reporting','batch_processing'])

    # 8. Legacy/file exchange.
    run_case('08_legacy_file_exchange', form(
        task_type='legacy_integration', business_situations=['legacy_integration','batch_processing'], legacy='file_only', load_profile='low', rps='1', latency_sla='daily', freshness_requirement='daily', allowed_channels=['sftp','etl'], forbidden_channels=['rest','kafka'], orchestration='external', chain_depth='single_level', step_count='2_3', result_model='report', source_of_truth='external', ownership='external', replay='rebuild',
        systems_matrix='Legacy | file export | Legacy | critical | sftp | non_blocking | 1d\nETL | loader | Data | important | sftp,etl | non_blocking | 1d',
        process_steps='0 | 1 | root | Получить файл | Legacy | sftp | csv | fileId | 1d | yes | quarantine | non_blocking | Data\n1 | 2 | 1 | Загрузить файл | ETL | etl | csv | loadId | 1d | yes | error report | non_blocking | Data'
    ), expect_name='Batch/File Integration', expect_patterns=['file'])

    # 9. Карточка 360 / BFF partial response.
    run_case('09_customer_360_multi_source', form(
        task_type='new_from_scratch', business_situations=['multi_source_aggregation','many_sources_one_consumer','highload_read','external_api_dependency'], customer_visible='no', read_frequency='high', response_time_expectation='under_1s', freshness_requirement='up_to_15m', business_priority='speed', unavailable_behavior='partial_response', load_profile='medium', latency_sla='subsecond', consistency='eventual_ok', orchestration='hybrid', chain_depth='fanout_fanin', step_count='4_7', result_model='sync', source_of_truth='external', ownership='field_level',
        systems_matrix='CRM | profile | CRM | important | rest | blocking | 2s\nABS | accounts | ABS | critical | rest | blocking | 2s\nKYC | checks | Compliance | critical | rest | blocking | 3s',
        process_steps='0 | 1 | root | CRM block | CRM | rest | id | profile | 2s | yes | partial | blocking | CRM\n0 | 2 | root | ABS block | ABS | rest | id | accounts | 2s | yes | partial | blocking | ABS\n0 | 3 | root | KYC block | KYC | rest | id | kyc | 3s | yes | partial | blocking | KYC\n1 | 4 | 1,2,3 | Compose card | BFF | internal | parts | card | 1s | no | partial response | blocking | App'
    ), expect_name='BFF/API Composition with Partial Response', expect_patterns=['gateway','fallback','rest'], expect_business=['multi_source_aggregation'])

    # 10. Reference data/versioned cache.
    run_case('10_reference_data', form(
        task_type='new_from_scratch', business_situations=['reference_data','highload_read'], read_frequency='very_high', change_frequency='rare', freshness_requirement='up_to_1h', response_time_expectation='under_100ms', load_profile='highload', rps='5000', latency_sla='subsecond', consistency='eventual_ok', orchestration='single', chain_depth='single_level', step_count='1', result_model='sync',
        systems_matrix='Reference API | dictionaries | Platform | important | rest | blocking | 100ms',
        process_steps='0 | 1 | root | Read dictionary | Reference API | rest | dictionaryCode | values,version | 100ms | no | stale | blocking | Platform'
    ), expect_name='Reference Data API + Versioned Cache', expect_patterns=['cache'], expect_business=['reference_data'])

    # 11. Async heavy processing/job.
    run_case('11_async_heavy_job', form(
        task_type='new_from_scratch', business_situations=['async_heavy_processing','batch_processing'], response_time_expectation='async_ok', unavailable_behavior='queue_for_later', load_profile='medium', latency_sla='hours', consistency='eventual_ok', orchestration='orchestrator', chain_depth='multi_level', step_count='4_7', result_model='tracking', delivery='at_least_once', replay='short',
        systems_matrix='Upload API | accept job | Product | critical | rest | blocking | 1s\nWorker | processing | Platform | critical | queue | non_blocking | 1h\nObject Storage | result | Platform | important | sftp | non_blocking | 1h',
        process_steps='0 | 1 | root | Accept file | Upload API | rest | file | jobId | 1s | no | reject | blocking | Product\n1 | 2 | 1 | Process file | Worker | queue | jobId | result | 1h | yes | dlq | non_blocking | Platform\n2 | 3 | 2 | Save result | Object Storage | sftp | result | link | 1h | yes | retry | non_blocking | Platform'
    ), expect_name='Async Job / Heavy Processing Flow', expect_patterns=['queue','inbox'])

    # 12. Near real-time decision.
    run_case('12_near_real_time_antifraud', form(
        task_type='event_domain', business_situations=['near_real_time_decision','highload_write_stream','external_api_dependency'], response_time_expectation='under_100ms', freshness_requirement='up_to_5s', load_profile='highload', rps='10000', peak_factor='10', latency_sla='subsecond', consistency='eventual_ok', delivery='at_least_once', ordering='per_entity', replay='long', orchestration='hybrid', chain_depth='multi_level', step_count='4_7', result_model='sync',
        systems_matrix='Transaction API | transaction | Payments | critical | rest | blocking | 50ms\nFeature Store | features | ML | critical | cache | blocking | 20ms\nKafka | stream | Platform | critical | kafka | non_blocking | 1s',
        process_steps='0 | 1 | root | Check transaction | Transaction API | rest | txn | decision | 100ms | no | fallback decision | blocking | Payments\n1 | 2 | 1 | Read features | Feature Store | cache | customerId | features | 20ms | no | fallback | blocking | ML\n1 | 3 | 1 | Publish event | Kafka | kafka | txn | event | 1s | yes | outbox | non_blocking | Platform'
    ), expect_name='Near Real-time Decision Flow', expect_patterns=['kafka','cache','fallback'])

    # 13. Migration/strangler.
    run_case('13_migration_strangler', form(
        task_type='replace_legacy', business_situations=['migration_or_strangler','legacy_integration','data_synchronization'], existing_state='legacy', compatibility='parallel', rollout='parallel', load_profile='medium', consistency='eventual_ok', orchestration='hybrid', chain_depth='multi_level', step_count='4_7', result_model='sync', source_of_truth='external', ownership='field_level', replay='rebuild',
        systems_matrix='Gateway | routing | Platform | critical | rest | blocking | 1s\nOld CRM | legacy | CRM | critical | rest,cdc | blocking | 3s\nNew CRM | target | CRM2 | critical | rest,kafka | blocking | 1s',
        process_steps='0 | 1 | root | Route request | Gateway | rest | request | route | 1s | no | fallback old | blocking | Platform\n1 | 2 | 1 | Execute old/new | Old CRM,New CRM | rest | data | result | 3s | yes | rollback route | blocking | CRM\n2 | 3 | 2 | Shadow compare | Gateway | cdc/event | old,new | diff | 5m | yes | manual review | non_blocking | Platform'
    ), expect_name='Migration / Strangler Fig', expect_patterns=['gateway','cdc','fallback'])

    # 14. Синхронизация данных / source of truth.
    run_case('14_data_sync_source_of_truth', form(
        task_type='data_migration', business_situations=['data_synchronization','many_sources_one_consumer'], source_of_truth='external', ownership='field_level', consistency='eventual_ok', delivery='at_least_once', ordering='per_entity', replay='rebuild', orchestration='hybrid', chain_depth='multi_level', step_count='4_7', result_model='report',
        systems_matrix='CRM | customer source | CRM | critical | cdc,event | non_blocking | 1m\nABS | account source | ABS | critical | cdc,event | non_blocking | 1m\nProfile Service | golden view | Platform | critical | kafka | blocking | 1s',
        process_steps='0 | 1 | root | CRM change | CRM | cdc | customer | event | 1m | yes | retry | non_blocking | CRM\n0 | 2 | root | ABS change | ABS | cdc | account | event | 1m | yes | retry | non_blocking | ABS\n1 | 3 | 1,2 | Merge profile | Profile Service | kafka | events | goldenRecord | 1s | yes | reconciliation | blocking | Platform'
    ), expect_name='Data Synchronization / Source-of-Truth Sync', expect_patterns=['cdc','kafka','inbox'])

    # 15. Конфликт требований: 100ms + strict freshness + unstable external provider.
    run_case('15_business_conflict_speed_strict_external', form(
        task_type='new_from_scratch', business_situations=['client_status_screen','external_api_dependency','unstable_external_provider'], customer_visible='yes', read_frequency='very_high', response_time_expectation='under_100ms', freshness_requirement='strict', business_priority='speed', external_dependency_stability='unstable', stale_data_impact='financial', unavailable_behavior='show_error', load_profile='highload', rps='2000', latency_sla='subsecond', consistency='strong', orchestration='single', chain_depth='single_level', step_count='1',
        systems_matrix='Mobile API | screen | App | critical | rest | blocking | 100ms\nExternal Core | source | Partner | critical | rest | blocking | 3s',
        process_steps='0 | 1 | root | Read strict value | Mobile API | rest | id | value | 100ms | yes | error | blocking | App'
    ), expect_conflict=True)

    # 16. Strict ordering of status events.
    run_case('16_strict_ordering_statuses', form(
        task_type='event_domain', business_situations=['strict_ordering_required','client_status_screen','highload_write_stream'], consistency='eventual_ok', delivery='at_least_once', ordering='per_entity', replay='long', load_profile='highload', orchestration='choreography', chain_depth='fanout', step_count='4_7', result_model='tracking',
        systems_matrix='Status Service | source | Core | critical | kafka | blocking | 1s\nProjection | read model | App | critical | event | non_blocking | 5s',
        process_steps='0 | 1 | root | Publish status vN | Status Service | kafka | status,version | event | 1s | yes | outbox | blocking | Core\n1 | 2 | 1 | Apply in order | Projection | event | event | projection | 5s | yes | dlq | non_blocking | App'
    ), expect_patterns=['kafka','inbox'], expect_business=['strict_ordering_required'])

    print('Passed 16 full SA scenario tests')


if __name__ == '__main__':
    main()
