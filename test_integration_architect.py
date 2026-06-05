# -*- coding: utf-8 -*-
"""Smoke/regression tests for integration_architect_pro.py.
Run: python test_integration_architect.py
"""
from integration_architect_pro import Engine, SolutionAuditor, defaults


def base_form(**overrides):
    f = defaults()
    f.update(overrides)
    return f


def test_simple_rest_is_not_polluted_by_e2e_defaults():
    f = base_form(
        preset_name='simple_rest',
        project_name='Простая REST-интеграция заявки с CRM',
        task_type='new_from_scratch',
        business_goal='Сайт отправляет заявку, API сохраняет её и создаёт карточку в CRM.',
        criticality='medium',
        load_profile='low', rps='20', peak_factor='2', latency_sla='seconds', consistency='strong',
        existing_state='none', change_policy=['add_api','add_status','change_db'], existing_capabilities=['rest_api','status_model','monitoring'],
        orchestration='single', chain_depth='single_level', step_count='2_3', result_model='sync', failure_policy='retry',
        source_system='Web/API',
        systems_matrix='Web/API | приём заявки | Продуктовая команда | important | rest | blocking | 2s\nCRM | карточка клиента | Команда CRM | important | rest | blocking | 5s',
        main_entity='Application',
        process_steps='0 | 1 | root | Принять заявку | Web/API | rest | clientId,amount | applicationId | 2s | no | reject | blocking | Продуктовая команда\n1 | 2 | 1 | Создать карточку CRM | CRM | rest | applicationId | crmId | 5s | yes | CRM_ERROR | blocking | Команда CRM',
        fields='clientId:uuid|required|indexed|sensitive, amount:decimal|required, idempotencyKey:string|unique, crmId:string|indexed',
        source_of_truth='own_db', ownership='single', data_volume='small', history='status_audit', retention='1_year',
        delivery='strict', ordering='no', replay='no',
        error_matrix='crm_timeout | CRM | blocking | yes | CRM_ERROR + manual task | Команда CRM',
        allowed_channels=['rest'], forbidden_channels=['kafka','sftp','soap'], legacy='none', dwh='no',
        sensitivity='pii', auth='service_and_user', availability='basic', observability='standard', rollout='feature_toggle', testing='integration'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] in {'Basic API + DB', 'REST API + OpenAPI'} or 'Basic API' in res['recommended']['name']
    assert not res['traits']['chain']
    assert not res['traits']['dwh']
    assert all('DWH' not in s.get('system','') for s in res['ctx']['steps'])
    assert res['recommended']['score'] <= 100


def test_complex_fanout_fanin_gets_orchestrated_join_solution():
    f = base_form(
        project_name='Сложная E2E цепочка', task_type='e2e_chain', business_goal='Принять заявку, провести скоринг, разослать статусы в CRM/уведомления/DWH и собрать итоговый статус.', source_system='API', main_entity='Application', fields='applicationId:uuid|required|unique, idempotencyKey:string|required|unique, status:string|required', source_of_truth='own_db', ownership='single', retention='3_years', load_profile='highload', rps='800', peak_factor='10',
        orchestration='orchestrator', chain_depth='fanout_fanin', step_count='8_plus', result_model='tracking', failure_policy='retry_compensate_manual',
        dwh='near_realtime', allowed_channels=['rest','kafka','queue','cdc','etl'], delivery='business_exactly_once', ordering='per_entity', replay='rebuild',
        process_steps='0 | 1 | root | accept | API | rest | in | out | 1s | no | reject | blocking | team\n1 | 2 | 1 | score | Scoring | queue | in | out | 5s | yes | manual | blocking | risk\n2 | 3 | 2 | event | Broker | kafka | in | event | 1s | yes | outbox | blocking | platform\n3 | 4 | 3 | crm | CRM | event | in | out | 30s | yes | dlq | non_blocking | crm\n3 | 5 | 3 | notify | Notify | event | in | out | 1m | yes | dlq | non_blocking | comm\n3 | 6 | 3 | dwh | DWH | cdc/etl | in | out | 15m | yes | replay | non_blocking | data\n4 | 7 | 4,5,6 | join | Process Manager | db | branches | final | 30s | yes | manual | blocking | platform',
        systems_matrix='API | command | team | critical | rest | blocking | 1s\nScoring | score | risk | critical | queue | blocking | 5s\nBroker | events | platform | critical | kafka | blocking | 1s\nCRM | customer | crm | important | event | non_blocking | 30s\nNotify | notifications | comm | non_critical | event | non_blocking | 1m\nDWH | analytics | data | important | cdc,etl | non_blocking | 15m'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Fan-out/Fan-in Orchestrated Process'
    assert 'saga' in res['recommended']['pattern_ids']
    assert res['traits']['fanout']
    assert res['readiness']['score'] >= 60


def test_unknown_orchestration_blocks_complex_chain():
    f = base_form(task_type='e2e_chain', orchestration='unknown', step_count='8_plus', chain_depth='multi_level')
    res = Engine().generate(f)
    assert res['recommended']['blocked'] is True
    assert res['readiness']['score'] <= 45


def test_audit_detects_core_production_risks_and_no_demo_hardcode_needed():
    f = base_form(task_type='audit_existing_solution', load_profile='highload', rps='500', peak_factor='5', audit_depth='deep')
    res = SolutionAuditor().audit(f)
    ids = {x['id'] for x in res['anti_patterns']}
    assert 'db_event_without_outbox' in ids
    assert 'async_without_idempotency' in ids
    assert 'observed_stuck_status' in ids
    assert res['recommended']['score'] < 80


def test_event_choreography_chain_prefers_event_choreography():
    f = base_form(
        project_name='Событийная доменная модель заказов', task_type='event_domain', load_profile='medium', rps='150', peak_factor='2',
        orchestration='choreography', chain_depth='fanout', step_count='4_7', result_model='notification', failure_policy='partial',
        allowed_channels=['rest','kafka','queue'], delivery='at_least_once', ordering='per_entity', replay='long', dwh='no',
        existing_state='production', change_policy=['add_event','add_outbox','add_status'], existing_capabilities=['rest_api','kafka','outbox','dlq','monitoring'],
        systems_matrix='Order Service | владелец заказа | team | critical | rest,kafka | blocking | 2s\nBilling | оплата | payments | critical | event | non_blocking | 30s\nNotification | уведомления | comm | non_critical | event | non_blocking | 1m\nLoyalty | бонусы | loyalty | important | event | non_blocking | 1m',
        process_steps='0 | 1 | root | Создать заказ | Order Service | rest | order | orderId | 2s | no | reject | blocking | team\n1 | 2 | 1 | Опубликовать OrderCreated | Order Service | kafka | order | event | 1s | yes | outbox retry | blocking | team\n2 | 3 | 2 | Списать оплату | Billing | event | event | paymentStatus | 30s | yes | dlq | non_blocking | payments\n2 | 4 | 2 | Отправить уведомление | Notification | event | event | notificationId | 1m | yes | dlq | non_blocking | comm\n2 | 5 | 2 | Начислить бонусы | Loyalty | event | event | loyaltyStatus | 1m | yes | dlq | non_blocking | loyalty'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Event Choreography'
    assert 'kafka' in res['recommended']['pattern_ids']
    assert 'outbox' in res['recommended']['pattern_ids']


def test_no_changes_existing_flow_prefers_non_invasive_extension():
    f = base_form(
        project_name='Нельзя менять production, нужен DWH', task_type='add_to_existing', existing_state='production',
        change_policy=['no_changes','read_only'], legacy='no_changes', load_profile='medium', rps='100', peak_factor='2',
        dwh='near_realtime', allowed_channels=['cdc','etl'], forbidden_channels=['rest','kafka'], orchestration='external',
        chain_depth='single_level', step_count='1', result_model='report', source_of_truth='external', ownership='external',
        systems_matrix='Core DB | источник данных | Core team | critical | cdc | non_blocking | 5m\nDWH | аналитика | Data team | important | cdc,etl | non_blocking | 15m',
        process_steps='0 | 1 | root | Читать изменения из БД | Core DB | cdc | changed rows | change events | 5m | yes | retry offset | non_blocking | Data team\n1 | 2 | 1 | Загрузить в DWH | DWH | etl | change events | dwh rows | 15m | yes | reconciliation | non_blocking | Data team'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Non-invasive Existing Process Extension'
    assert res['db']['target_only'] is True


def test_file_legacy_chooses_batch_file_integration():
    f = base_form(
        project_name='Legacy file exchange', task_type='legacy_integration', existing_state='legacy', legacy='file_only',
        load_profile='low', rps='1', peak_factor='1', latency_sla='daily', result_model='report', orchestration='external',
        chain_depth='single_level', step_count='2_3', allowed_channels=['sftp','etl'], forbidden_channels=['kafka'], dwh='batch',
        systems_matrix='Legacy АБС | выгрузка файла | Legacy team | critical | sftp | non_blocking | 1d\nETL | обработка файла | Data team | important | sftp,etl | non_blocking | 1d',
        process_steps='0 | 1 | root | Получить файл | Legacy АБС | sftp | csv | fileId | 1d | yes | quarantine | non_blocking | Data team\n1 | 2 | 1 | Загрузить файл | ETL | etl | csv | loadId | 1d | yes | error report | non_blocking | Data team'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] in {'Batch/File Integration', 'Data Pipeline / DWH'}
    assert 'file' in {p['id'] for p in res['patterns']}


def test_business_context_activates_cache_read_model_and_fallback():
    f = base_form(
        project_name='Клиентский экран статуса заявки', task_type='e2e_chain', business_goal='Клиент часто смотрит статус заявки, источник статуса может отвечать медленно.',
        business_situations=['client_status_screen','highload_read','external_api_dependency'], customer_visible='yes', money_impact='no', regulatory_impact='no',
        read_frequency='very_high', change_frequency='medium', response_time_expectation='under_300ms', freshness_requirement='up_to_1m', business_priority='speed', stale_data_impact='support', unavailable_behavior='show_stale', external_dependency_stability='unstable',
        load_profile='highload', rps='1200', peak_factor='10', latency_sla='subsecond', consistency='eventual_ok', result_model='tracking', orchestration='orchestrator', chain_depth='multi_level', step_count='4_7',
        allowed_channels=['rest','kafka','queue'], delivery='at_least_once', ordering='per_entity', replay='short'
    )
    res = Engine().generate(f)
    pids = {p['id'] for p in res['patterns']}
    assert 'cache' in pids
    assert 'read_model_business' in pids
    assert 'fallback' in pids
    assert 'client_status_screen' in res['ctx']['business']['active_scenarios']
    assert any('last_updated' in x for x in res['ctx']['business']['derived_requirements'])


def test_business_conflict_speed_strict_freshness_external_dependency_is_flagged():
    f = base_form(
        project_name='Строго актуальный быстрый экран с внешним API', task_type='new_from_scratch',
        business_situations=['client_status_screen','external_api_dependency'], customer_visible='yes', read_frequency='very_high', response_time_expectation='under_100ms', freshness_requirement='strict', business_priority='freshness', unavailable_behavior='show_error', external_dependency_stability='unstable',
        load_profile='highload', rps='1000', peak_factor='5', latency_sla='subsecond', orchestration='single', chain_depth='single_level', step_count='2_3', result_model='sync', allowed_channels=['rest'], dwh='no'
    )
    res = Engine().generate(f)
    ids = {a['id'] for a in res['anti_patterns']}
    assert any(i.startswith('business_conflict_') for i in ids)
    assert res['ctx']['business']['conflicts']


def test_hot_client_status_selects_fast_read_cached_model():
    f = base_form(
        project_name='Горячий клиентский экран статуса', task_type='new_from_scratch',
        business_situations=['client_status_screen','highload_read','external_api_dependency'],
        business_goal='Клиент часто открывает экран статуса заявки, внешний CRM отвечает медленно.',
        user_action='Смотрит статус заявки', customer_visible='yes', read_frequency='very_high', change_frequency='daily',
        response_time_expectation='under_300ms', freshness_requirement='up_to_1m', business_priority='speed',
        stale_data_impact='support', unavailable_behavior='show_stale', external_dependency_stability='limited',
        load_profile='highload', rps='1000', peak_factor='10', orchestration='single', chain_depth='single_level', step_count='1',
        result_model='tracking', allowed_channels=['rest','kafka','queue','cdc'], dwh='no', legacy='none', delivery='at_least_once', ordering='per_entity', replay='short',
        systems_matrix='CRM | источник статуса | CRM | critical | rest | blocking | 3s',
        process_steps='1 | 1 | root | Получить статус | CRM | rest | applicationId | status | 3s | yes | none | blocking | CRM',
        fields='applicationId:uuid|required|indexed, status:string|required, lastUpdated:datetime|required'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Fast Read / Cached Read Model'
    assert {'cache','read_model_business','fallback'}.issubset(set(res['recommended']['pattern_ids']))
    assert any('last_updated' in x for x in res['ctx']['business']['derived_requirements'])


def test_webhook_callback_selects_inbox_processing():
    f = base_form(
        project_name='Callback статуса платежа', task_type='external_partner',
        business_situations=['webhook_callback','external_api_dependency','exactly_once_required'],
        business_goal='Партнёр присылает callback результата платежа, его нельзя обработать дважды.',
        customer_visible='mixed', money_impact='yes', response_time_expectation='under_1s', freshness_requirement='up_to_5s',
        unavailable_behavior='queue_for_later', orchestration='single', chain_depth='single_level', step_count='1', result_model='callback',
        allowed_channels=['rest','webhook','queue','kafka'], delivery='business_exactly_once', ordering='per_entity', replay='short', dwh='no',
        systems_matrix='Partner | webhook source | Partner | critical | webhook | non_blocking | 5s',
        process_steps='1 | 1 | root | Принять callback | Partner | webhook | event | ack | 1s | yes | none | non_blocking | API',
        fields='external_event_id:string|required|unique, operation_id:string|required|indexed'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Webhook Intake + Inbox Processing'
    assert {'webhook','inbox','queue'}.issubset(set(res['recommended']['pattern_ids']))
    assert any('Callback/webhook' in x for x in res['ctx']['business']['derived_requirements'])


def test_regulatory_batch_dwh_selects_data_pipeline():
    f = base_form(
        project_name='Регуляторная отчётность', task_type='dwh_analytics',
        business_situations=['dwh_reporting','batch_processing','personal_data_exchange','regulatory_process'],
        business_goal='Ночью сформировать регуляторную витрину по операциям.', customer_visible='no', regulatory_impact='yes',
        response_time_expectation='async_ok', freshness_requirement='daily', load_profile='medium', latency_sla='daily', dwh='regulatory',
        orchestration='single', chain_depth='single_level', step_count='2_3', result_model='report', allowed_channels=['sftp','cdc','etl','rest'],
        delivery='at_least_once', ordering='no', replay='rebuild', sensitivity='pii',
        systems_matrix='Core | операции | Core | critical | cdc | non_blocking | daily\nDWH | отчетность | Data | critical | etl | non_blocking | daily',
        process_steps='1 | 1 | root | Выгрузить операции | Core | cdc | changes | staging | daily | yes | none | non_blocking | Data\n1 | 2 | 1 | Собрать витрину | DWH | etl | staging | report | daily | yes | reconciliation | non_blocking | Data'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Data Pipeline / DWH'
    assert {'cdc','etl'}.issubset(set(res['recommended']['pattern_ids']))
    assert any('lineage' in x for x in res['ctx']['business']['derived_requirements'])


def test_multi_source_aggregation_has_partial_response_requirements():
    f = base_form(
        project_name='Карточка клиента 360', task_type='new_from_scratch',
        business_situations=['multi_source_aggregation','many_sources_one_consumer','highload_read','external_api_dependency'],
        business_goal='Оператор открывает карточку клиента из CRM, ABS и KYC.', user_action='Открывает карточку клиента',
        customer_visible='no', read_frequency='high', change_frequency='medium', response_time_expectation='under_1s',
        freshness_requirement='up_to_15m', business_priority='speed', unavailable_behavior='partial_response',
        orchestration='hybrid', chain_depth='fanout_fanin', step_count='4_7', result_model='sync', allowed_channels=['rest','queue','kafka'], delivery='at_least_once',
        systems_matrix='CRM | профиль | CRM | important | rest | blocking | 2s\nABS | счета | ABS | critical | rest | blocking | 2s\nKYC | проверки | Compliance | critical | rest | blocking | 3s',
        process_steps='1 | 1 | root | Запросить CRM | CRM | rest | id | profile | 2s | yes | none | blocking | CRM\n1 | 2 | root | Запросить ABS | ABS | rest | id | accounts | 2s | yes | none | blocking | ABS\n1 | 3 | root | Запросить KYC | KYC | rest | id | kyc | 3s | yes | none | blocking | KYC\n1 | 4 | root | Собрать ответ | BFF | internal | parts | card | 1s | no | none | blocking | App'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] in {'Fan-out/Fan-in Orchestrated Process','BFF/API Composition with Partial Response'}
    assert any('partial response' in x for x in res['ctx']['business']['derived_requirements'])

def test_financial_operation_prefers_operation_state_machine():
    f = base_form(
        project_name='Финансовая операция', task_type='external_partner',
        business_situations=['financial_operation','external_api_dependency','exactly_once_required','regulatory_process'],
        customer_visible='yes', money_impact='yes', regulatory_impact='yes', response_time_expectation='under_3s', freshness_requirement='strict',
        stale_data_impact='financial', unavailable_behavior='manual_review', external_dependency_stability='limited',
        load_profile='medium', rps='150', peak_factor='5', latency_sla='seconds', consistency='business_exactly_once',
        orchestration='orchestrator', chain_depth='multi_level', step_count='4_7', result_model='tracking', failure_policy='retry_compensate_manual',
        allowed_channels=['rest','webhook','queue','kafka'], delivery='business_exactly_once', ordering='per_entity', replay='long', dwh='regulatory', sensitivity='financial', observability='regulated',
        process_steps='0 | 1 | root | create operation | API | rest/db | request | operationId | 1s | no | reject | blocking | payments\n1 | 2 | 1 | call partner | Partner | rest | operation | accepted | 5s | yes | manual | blocking | partner',
        systems_matrix='API | operation owner | payments | critical | rest | blocking | 1s\nPartner | execution | partner | critical | rest | blocking | 5s',
        fields='operationId:uuid|required|indexed, idempotencyKey:string|required|unique, amount:decimal|required'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Financial Operation State Machine'
    assert {'postgres','inbox'}.issubset(set(res['recommended']['pattern_ids']))


def test_async_heavy_processing_prefers_job_flow():
    f = base_form(
        project_name='Загрузка файла и расчёт отчёта', task_type='new_from_scratch',
        business_situations=['async_heavy_processing','batch_processing'], customer_visible='yes',
        response_time_expectation='async_ok', freshness_requirement='up_to_1h', unavailable_behavior='queue_for_later',
        load_profile='medium', rps='20', peak_factor='2', latency_sla='hours', orchestration='single', chain_depth='single_level', step_count='2_3', result_model='tracking',
        allowed_channels=['rest','queue'], delivery='at_least_once', ordering='no', replay='short', dwh='no',
        process_steps='0 | 1 | root | accept file | API | rest | file | jobId | 1s | no | reject | blocking | product\n1 | 2 | 1 | process file | Worker | queue | jobId | result | 1h | yes | DLQ | non_blocking | platform',
        systems_matrix='API | accept task | product | important | rest | blocking | 1s\nWorker | processing | platform | important | queue | non_blocking | 1h',
        fields='jobId:uuid|required|indexed, fileId:string|required|unique'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Async Job / Heavy Processing Flow'
    assert 'queue' in res['recommended']['pattern_ids']


def test_migration_strangler_prefers_migration_variant():
    f = base_form(
        project_name='Миграция CRM', task_type='replace_legacy',
        business_situations=['migration_or_strangler','legacy_integration','data_synchronization'],
        existing_state='legacy', legacy='soap_only', compatibility='parallel', rollout='parallel',
        load_profile='medium', rps='300', peak_factor='5', orchestration='hybrid', chain_depth='multi_level', step_count='4_7', result_model='tracking',
        allowed_channels=['rest','soap','cdc','queue'], delivery='at_least_once', ordering='per_entity', replay='rebuild', dwh='near_realtime',
        process_steps='0 | 1 | root | route request | Gateway | rest | req | route | 1s | no | fallback | blocking | platform\n1 | 2 | 1 | call old crm | Old CRM | soap | req | result | 3s | yes | fallback | blocking | crm\n1 | 3 | 1 | call new crm | New CRM | rest | req | result | 1s | yes | rollback | blocking | crm2',
        systems_matrix='Gateway | routing | platform | critical | rest | blocking | 1s\nOld CRM | legacy | crm | critical | soap | blocking | 3s\nNew CRM | target | crm2 | critical | rest | blocking | 1s',
        fields='customerId:uuid|required|indexed'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] in {'Migration / Strangler Fig','SOAP Legacy Adapter Integration'}
    assert 'migration_or_strangler' in res['ctx']['business']['active_scenarios']


def test_reference_data_prefers_versioned_cache():
    f = base_form(
        project_name='Справочник тарифов', task_type='new_from_scratch',
        business_situations=['reference_data','highload_read'], customer_visible='mixed', read_frequency='very_high', change_frequency='daily', response_time_expectation='under_300ms', freshness_requirement='up_to_15m', business_priority='speed', stale_data_impact='support', unavailable_behavior='show_stale',
        load_profile='highload', rps='2000', peak_factor='10', orchestration='single', chain_depth='single_level', step_count='1', result_model='sync',
        allowed_channels=['rest'], delivery='at_least_once', ordering='no', replay='short', dwh='no',
        process_steps='0 | 1 | root | get tariff | Tariff API | rest | tariffCode | tariff | 300ms | no | stale | blocking | product',
        systems_matrix='Tariff API | source of truth | product | important | rest | blocking | 300ms', fields='tariffCode:string|required|indexed, version:int|required'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] in {'Reference Data API + Versioned Cache','Fast Read / Cached Read Model'}
    assert 'cache' in {p['id'] for p in res['patterns']}


def test_near_real_time_decision_prefers_stream_decision_flow():
    f = base_form(
        project_name='Near real-time антифрод', task_type='event_domain',
        business_situations=['near_real_time_decision','highload_write_stream','external_api_dependency'], customer_visible='no', money_impact='yes',
        response_time_expectation='under_300ms', freshness_requirement='up_to_5s', business_priority='speed', stale_data_impact='financial', unavailable_behavior='manual_review',
        load_profile='highload', rps='1500', peak_factor='10', latency_sla='subsecond', orchestration='choreography', chain_depth='fanout', step_count='4_7', result_model='notification',
        allowed_channels=['rest','kafka','queue'], delivery='at_least_once', ordering='per_entity', replay='long', dwh='near_realtime',
        process_steps='0 | 1 | root | publish transaction | Payments | kafka | tx | event | 100ms | yes | outbox | blocking | payments\n1 | 2 | 1 | score fraud | Fraud | kafka | event | decision | 300ms | yes | manual | non_blocking | risk',
        systems_matrix='Payments | source | payments | critical | kafka | blocking | 100ms\nFraud | decision | risk | critical | kafka,rest | non_blocking | 300ms',
        fields='transactionId:uuid|required|indexed, amount:decimal|required'
    )
    res = Engine().generate(f)
    assert res['recommended']['name'] in {'Near Real-time Decision Flow','Event Choreography'}
    assert 'near_real_time_decision' in res['ctx']['business']['active_scenarios']
if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for t in tests:
        t()
        print('OK', t.__name__)
    print(f'Passed {len(tests)} tests')
