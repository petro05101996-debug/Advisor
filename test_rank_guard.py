#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from integration_architect_pro import Engine, defaults


def form(**kw):
    f = defaults()
    f.update({
        'project_name':'rank guard',
        'business_goal':'Сложный production бизнес-процесс с несколькими интеграционными слоями.',
        'source_system':'Mobile/API',
        'main_entity':'applicationId',
        'fields':'applicationId:uuid|required|unique|indexed, clientId:uuid|required|indexed|sensitive, idempotencyKey:string|required|unique, status:string|required',
        'source_of_truth':'own_db',
        'ownership':'single',
        'retention':'5_years',
        'allowed_channels':['rest','kafka','queue','webhook','cdc','etl','soap','sftp'],
        'forbidden_channels':['direct_db_write'],
    })
    f.update(kw)
    return f


def assert_rec(name, f, expected, not_expected=()):
    res = Engine().generate(f)
    rec = res['recommended']['name']
    assert rec == expected, f'{name}: expected {expected}, got {rec}; variants={[(v["name"], v["score"], v.get("_priority")) for v in res["variants"][:6]]}'
    for bad in not_expected:
        assert rec != bad, f'{name}: forbidden top-level {bad}'
    print(f'OK {name}: {rec}, score={res["recommended"]["score"]}, readiness={res["readiness"]["score"]}')
    return res


def test_legacy_soap_inside_complex_e2e_is_not_top_level():
    f=form(
        task_type='e2e_chain',
        business_situations=['application_or_order_creation','multi_step_business_process','client_status_screen','financial_operation','webhook_callback','external_api_dependency','dwh_reporting','legacy_integration','personal_data_exchange','regulatory_process','strict_ordering_required','long_running_process','exactly_once_required','unstable_external_provider','peak_load_process'],
        customer_visible='yes', money_impact='yes', regulatory_impact='yes',
        response_time_expectation='under_300ms', freshness_requirement='up_to_1m', stale_data_impact='financial', unavailable_behavior='show_stale', external_dependency_stability='unstable',
        load_profile='highload', rps='1200', peak_factor='10', latency_sla='async_minutes',
        consistency='business_exactly_once', delivery='business_exactly_once', ordering='per_entity', replay='rebuild',
        orchestration='orchestrator', chain_depth='fanout_fanin', step_count='8_plus', failure_policy='retry_compensate_manual', result_model='tracking',
        dwh='regulatory', legacy='soap_only', sensitivity='pii', observability='regulated',
        systems_matrix='Mobile API | клиентский вход | Product | critical | rest | blocking | 300ms\nKYC | проверка клиента | Compliance | critical | rest | blocking | 5s\nBKI | кредитный отчёт | External | critical | rest,webhook | blocking | 30s\nAntifraud | антифрод | Risk | critical | kafka | blocking | 5s\nScoring | решение | Risk | critical | queue | blocking | 30s\nLegacy ABS | выдача/договор | ABS | critical | soap | blocking | 10s\nCRM | карточка клиента | CRM | important | event | non_blocking | 1m\nDWH | регуляторика | Data | critical | cdc,etl | non_blocking | 1d',
        process_steps='0 | 1 | root | Принять заявку | Mobile API | rest | request | applicationId | 300ms | no | reject | blocking | Product\n1 | 2 | 1 | KYC | KYC | rest | applicationId | kycStatus | 5s | yes | manual | blocking | Compliance\n1 | 3 | 1 | Запросить БКИ | BKI | rest | applicationId | requestId | 5s | yes | manual | blocking | Risk\n1 | 4 | 3 | Принять callback БКИ | BKI | webhook | report | reportSaved | 30s | yes | inbox | blocking | Risk\n1 | 5 | 1 | Антифрод | Antifraud | kafka | application | fraudStatus | 5s | yes | dlq | blocking | Risk\n2 | 6 | 2,4,5 | Скоринг | Scoring | queue | checks | decision | 30s | yes | manual | blocking | Risk\n3 | 7 | 6 | Legacy ABS | Legacy ABS | soap | decision | contractStatus | 10s | yes | compensate | blocking | ABS\n4 | 8 | 7 | Опубликовать статус | Mobile API | kafka | status | event | 1s | yes | outbox | blocking | Product\n4 | 9 | 8 | CRM | CRM | event | status | crmUpdated | 1m | yes | dlq | non_blocking | CRM\n4 | 10 | 8 | DWH | DWH | cdc/etl | snapshot | report | 1d | yes | reconciliation | non_blocking | Data\n5 | 11 | 9,10 | Финальный статус | Mobile API | db | branches | finalStatus | 1m | yes | manual | blocking | Product'
    )
    res=assert_rec('hard_soap_legacy_layer', f, 'Fan-out/Fan-in Orchestrated Process', not_expected=('SOAP Legacy Adapter Integration','Data Pipeline / DWH','Webhook Intake + Inbox Processing'))
    names=[v['name'] for v in res['variants'][:5]]
    assert 'SOAP Legacy Adapter Integration' in names, 'SOAP adapter must still be present as a layer/variant, just not top-level'


def test_dwh_inside_core_flow_is_not_top_level():
    f=form(task_type='e2e_chain', business_situations=['application_or_order_creation','multi_step_business_process','dwh_reporting'], dwh='regulatory', load_profile='medium', orchestration='orchestrator', chain_depth='multi_level', step_count='4_7', result_model='tracking', delivery='at_least_once',
           systems_matrix='API | core | Product | critical | rest | blocking | 1s\nCore | process | Core | critical | queue | blocking | 10s\nDWH | data | Data | important | cdc,etl | non_blocking | 1d',
           process_steps='0 | 1 | root | Accept | API | rest | req | id | 1s | no | reject | blocking | Product\n1 | 2 | 1 | Process | Core | queue | id | done | 10s | yes | manual | blocking | Core\n2 | 3 | 2 | Export DWH | DWH | cdc/etl | row | report | 1d | yes | reconciliation | non_blocking | Data')
    assert_rec('dwh_is_layer_in_core_flow', f, 'Orchestrated E2E Process', not_expected=('Data Pipeline / DWH',))


def test_webhook_inside_financial_flow_is_not_top_level():
    f=form(task_type='external_partner', business_situations=['financial_operation','webhook_callback','external_api_dependency','exactly_once_required'], money_impact='yes', customer_visible='yes', delivery='business_exactly_once', consistency='business_exactly_once', orchestration='orchestrator', chain_depth='multi_level', step_count='4_7', result_model='tracking', failure_policy='retry_compensate_manual',
           systems_matrix='API | operation | Payments | critical | rest | blocking | 1s\nPartner | execute | Partner | critical | rest,webhook | blocking | 30s',
           process_steps='0 | 1 | root | Create operation | API | rest | req | operationId | 1s | no | reject | blocking | Payments\n1 | 2 | 1 | Call partner | Partner | rest | operation | accepted | 5s | yes | manual | blocking | Partner\n2 | 3 | 2 | Callback | Partner | webhook | result | finalStatus | 30s | yes | inbox | non_blocking | Partner')
    assert_rec('webhook_layer_in_financial_flow', f, 'Financial Operation State Machine', not_expected=('Webhook Intake + Inbox Processing',))


def main():
    test_legacy_soap_inside_complex_e2e_is_not_top_level()
    test_dwh_inside_core_flow_is_not_top_level()
    test_webhook_inside_financial_flow_is_not_top_level()
    print('Passed 3 rank guard tests')

if __name__ == '__main__':
    main()
