#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Жёсткие smoke/regression проверки для v4.8.8:
- широкий E2E highload credit-flow не должен сваливаться в технический publisher/cache/DWH;
- enrichment-before-Kafka ловит ownership и запрет Outbox/CDC;
- плохая синхронная финансовая цепочка блокируется quality gate;
- multi-source 360 выбирает composition/partial response;
- legacy file-only выбирает batch/file integration.
"""
from integration_architect_pro import Engine, defaults
from test_v48_2_final_hard_fixes import hard_design_form, enrichment_single_kafka_form


def anti_ids(res):
    return {a['id'] for a in res['anti_patterns']}


def test_brutal_highload_credit_e2e_keeps_core_architecture():
    res = Engine().generate(hard_design_form())
    assert res['recommended']['name'] == 'Orchestrated E2E Process'
    assert 'saga' in res['recommended']['pattern_ids']
    assert 'outbox' in res['recommended']['pattern_ids']
    assert 'inbox' in res['recommended']['pattern_ids']
    assert res['readiness']['score'] >= 60


def test_brutal_enrichment_no_outbox_or_cdc_is_not_silent():
    f = enrichment_single_kafka_form()
    f['change_policy'] = ['add_event']
    f['existing_capabilities'] = ['rest_api', 'status_model']
    res = Engine().generate(f)
    ids = anti_ids(res)
    assert 'event_ownership_vs_kafka_infra' in ids
    assert 'enrichment_requires_change_but_outbox_not_allowed' in ids
    assert res['readiness']['score'] < 75


def test_brutal_bad_sync_money_chain_is_blocked():
    f = defaults()
    f.update({
        'project_name':'Плохая синхронная цепочка оплаты',
        'task_type':'e2e_chain',
        'business_goal':'Клиент платит, система синхронно зовет несколько сервисов и внешнего партнера, ответ нужен за секунды.',
        'business_situations':['financial_operation','multi_step_business_process','external_api_dependency','exactly_once_required','personal_data_exchange'],
        'money_impact':'yes','regulatory_impact':'yes','customer_visible':'yes',
        'load_profile':'highload','rps':'700','peak_factor':'8','latency_sla':'seconds',
        'consistency':'business_exactly_once','delivery':'at_least_once',
        'orchestration':'unknown','chain_depth':'multi_level','step_count':'4_7','result_model':'sync','failure_policy':'retry',
        'fields':'paymentId:uuid|required|unique, customerId:uuid|required|sensitive, amount:decimal|required, status:string|required',
        'process_steps':'0 | 1 | root | Accept payment | Payment API | rest | request | paymentId | 1s | yes | none | blocking | Payments\n1 | 2 | 1 | Reserve money | ABS | rest | paymentId | reserveId | 2s | yes | none | blocking | ABS\n1 | 3 | 2 | Call partner | Partner | rest | reserveId | result | 5s | yes | none | blocking | Partner\n1 | 4 | 3 | Update CRM | CRM | rest | result | ok | 2s | yes | none | blocking | CRM',
        'systems_matrix':'Payment API | entry | Payments | critical | rest | blocking | 1s\nABS | accounts | Core | critical | rest | blocking | 2s\nPartner | processing | External | critical | rest | blocking | 5s\nCRM | customer | Sales | important | rest | blocking | 2s',
        'source_of_truth':'own_db','ownership':'single','retention':'not_defined',
        'allowed_channels':['rest'], 'forbidden_channels':['direct_db_write'],
        'sensitivity':'financial','auth':'none',
    })
    res = Engine().generate(f)
    ids = anti_ids(res)
    assert res['recommended']['name'].startswith('Architecture decision blocked')
    for expected in ['unknown_orchestration','sync_chain','no_idempotency','no_auth_sensitive','highload_low_latency_chain']:
        assert expected in ids
    assert res['readiness']['score'] == 0


def test_brutal_multi_source_360_uses_composition_not_saga():
    f = defaults()
    f.update({
        'project_name':'Карточка 360 частичный ответ','task_type':'new_from_scratch',
        'business_goal':'Оператор открывает карточку клиента, данные из CRM/ABS/KYC, медленный источник не должен ломать экран.',
        'business_situations':['multi_source_aggregation','many_sources_one_consumer','highload_read','external_api_dependency','personal_data_exchange'],
        'customer_visible':'no','money_impact':'indirect','regulatory_impact':'yes',
        'load_profile':'medium','rps':'250','peak_factor':'5','latency_sla':'seconds','consistency':'eventual_ok',
        'result_model':'sync','orchestration':'hybrid','chain_depth':'fanout_fanin','step_count':'4_7','failure_policy':'partial',
        'systems_matrix':'CRM | profile | CRM | important | rest | blocking | 2s\nABS | accounts | ABS | critical | rest | blocking | 2s\nKYC | checks | Compliance | critical | rest | blocking | 3s',
        'process_steps':'1 | 1 | root | Request CRM | CRM | rest | id | profile | 2s | yes | partial | blocking | CRM\n1 | 2 | root | Request ABS | ABS | rest | id | accounts | 2s | yes | partial | blocking | ABS\n1 | 3 | root | Request KYC | KYC | rest | id | kyc | 3s | yes | partial | blocking | KYC\n2 | 4 | 1,2,3 | Build card | BFF | internal | parts | card | 1s | no | partial response | blocking | App',
        'fields':'customerId:uuid|required|indexed|sensitive, blockFreshness:json|required',
        'source_of_truth':'external','ownership':'field_level','allowed_channels':['rest','queue','kafka'],
        'sensitivity':'pii','auth':'service_and_user','observability':'full'
    })
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'BFF/API Composition with Partial Response'
    assert 'fallback' in res['recommended']['pattern_ids']
    assert 'sync_chain' in anti_ids(res)


def test_brutal_legacy_file_only_uses_batch_file():
    f = defaults()
    f.update({
        'project_name':'Legacy file exchange','task_type':'legacy_integration',
        'business_goal':'Legacy выгружает файл раз в день. Нужно забрать, проверить, загрузить и переобработать.',
        'business_situations':['legacy_integration','batch_processing','dwh_reporting'],
        'load_profile':'low','rps':'1','latency_sla':'daily','consistency':'eventual_ok',
        'existing_state':'legacy','change_policy':['read_only'],'existing_capabilities':['batch'],
        'orchestration':'external','chain_depth':'single_level','step_count':'2_3','failure_policy':'retry','result_model':'report',
        'legacy':'file_only','dwh':'batch','allowed_channels':['sftp','etl'],'forbidden_channels':['rest','kafka'],
        'systems_matrix':'Legacy | file source | Legacy | critical | sftp | non_blocking | 1d\nETL | loader | Data | important | etl | non_blocking | 1d',
        'process_steps':'0 | 1 | root | Receive file | Legacy | sftp | csv | fileId | 1d | yes | quarantine | non_blocking | Data\n1 | 2 | 1 | Load file | ETL | etl | csv | loadId | 1d | yes | error report | non_blocking | Data',
        'fields':'fileId:string|required|unique, rowHash:string|required|indexed',
        'source_of_truth':'external','ownership':'external','retention':'3_years',
        'sensitivity':'internal','auth':'service','observability':'standard'
    })
    res = Engine().generate(f)
    assert res['recommended']['name'] == 'Batch/File Integration'
    assert 'file' in res['recommended']['pattern_ids']
