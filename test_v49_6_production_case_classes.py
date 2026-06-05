#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production-grade regression checks for case class → top-level → layers → gate."""
from integration_architect_pro import Engine, defaults


def test_db_plus_kafka_dual_write_selects_outbox_core_not_read_model():
    f = defaults()
    f.update({
        'project_name':'Order changed event','task_type':'event_domain',
        'business_goal':'Order Service updates order in DB and must publish OrderChanged to multiple consumers via Kafka.',
        'business_situations':['one_source_many_consumers','highload_write_stream'],
        'source_system':'Order Service','main_entity':'order','source_of_truth':'source','ownership':'single_owner',
        'load_profile':'medium','rps':'120','peak_factor':'2','latency_sla':'async_minutes','result_model':'notification',
        'change_policy':['add_outbox','add_event','add_status'],'allowed_channels':['rest','kafka'],
        'delivery':'at_least_once','ordering':'per_entity','replay':'long',
        'fields':'orderId:uuid|required|indexed, eventId:uuid|required|unique, aggregateVersion:int|required',
        'systems_matrix':'Order Service | owner | order | critical | db+kafka | non_blocking | 1m\nCRM | consumer | crm | important | kafka | non_blocking | 5m',
        'process_steps':'0 | 1 | root | Update order | Order Service | db | command | order | 1s | no | reject | blocking | order\n1 | 2 | 1 | Publish event | Outbox publisher | kafka | outbox | event | 1m | yes | DLQ | non_blocking | platform',
        'error_matrix':'kafka_error | publisher | non_blocking | yes | DLQ | platform'
    })
    res = Engine().generate(f)
    assert res['case_classes'][0]['id'] == 'dual_write_db_broker'
    assert res['recommended']['name'] == 'Event-driven + Transactional Outbox'
    assert res['recommended']['name'] != 'Fast Read / Cached Read Model'
    assert 'outbox' in res['recommended']['pattern_ids']
    assert 'inbox' in res['recommended']['pattern_ids']
    assert res['structured_result']['top_level_architecture'] == 'Event-driven + Transactional Outbox'


def test_financial_webhook_without_explicit_security_is_not_green():
    f = defaults()
    f.update({
        'project_name':'Payment webhook','task_type':'external_partner',
        'business_goal':'Payment provider sends webhook about payment status. Duplicates and retries are possible.',
        'business_situations':['webhook_callback','financial_operation','external_api_dependency'],
        'customer_visible':'yes','money_impact':'yes','regulatory_impact':'yes','security_boundary':'external','sensitivity':'financial',
        'result_model':'callback','allowed_channels':['webhook','queue','rest'],'delivery':'at_least_once','ordering':'per_entity','replay':'short',
        'webhook_signature_required':'unknown','webhook_raw_body_preserved':'unknown','webhook_reconciliation_available':'unknown',
        'source_system':'Payment Provider','main_entity':'payment','source_of_truth':'external','ownership':'external',
        'fields':'paymentId:string|required|indexed, eventId:string|required|unique, status:string|required',
        'systems_matrix':'Provider | sender | partner | critical | webhook | non_blocking | 3s\nPayments | receiver | payments | critical | queue | non_blocking | 1m',
        'process_steps':'0 | 1 | root | Receive webhook | Payments | webhook | payload | eventId | 3s | yes | inbox | non_blocking | payments\n1 | 2 | 1 | Update payment | Worker | queue | event | status | 1m | yes | DLQ | non_blocking | payments',
        'error_matrix':'duplicate | inbox | non_blocking | no | ignore | payments'
    })
    res = Engine().generate(f)
    assert res['case_classes'][0]['id'] in {'webhook_intake','financial_state_machine'}
    assert res['production_gate']['level'] in {'RED','AMBER','YELLOW'}
    assert any('Webhook security' in x or 'Webhook' in x for x in res['production_gate']['blocking_gaps'])


def test_enrichment_current_at_publish_is_high_not_critical_when_snapshot_export():
    f = defaults()
    f.update({
        'project_name':'Contract snapshot export','task_type':'event_domain',
        'business_goal':'Source owns contract changes; target needs enriched snapshot in single Kafka topic after REST enrichment.',
        'business_situations':['data_enrichment','one_source_many_consumers'],
        'event_payload_intent':'snapshot_export','enrichment_required':'critical','enrichment_channel':'rest','enrichment_consistency':'current_at_publish',
        'kafka_topology':'single_topic_only','source_has_kafka_infra':'no',
        'change_policy':['add_outbox','add_event'],'source_change_policy':'minimal_table_only','allowed_channels':['rest','kafka'],
        'delivery':'at_least_once','ordering':'per_entity','replay':'long','result_model':'notification',
        'source_system':'Contracts','main_entity':'contract','source_of_truth':'source','ownership':'single_owner',
        'fields':'contractId:uuid|required|indexed, eventId:uuid|required|unique, aggregateVersion:int|required, dataAsOf:datetime|required',
        'systems_matrix':'Contracts | source | contracts | critical | db | blocking | 1s\nPublisher | enrichment publisher | platform | important | kafka | non_blocking | 1m',
        'process_steps':'0 | 1 | root | Save contract | Contracts | db | command | contract | 1s | no | reject | blocking | contracts\n1 | 2 | 1 | Enrich and publish | Publisher | rest+kafka | outbox | enriched event | 1m | yes | FAILED | non_blocking | platform',
        'error_matrix':'enrichment_timeout | Publisher | non_blocking | yes | FAILED | platform'
    })
    res = Engine().generate(f)
    assert res['case_classes'][0]['id'] == 'data_enrichment_pipeline'
    assert res['recommended']['name'] == 'Outbox + REST Enrichment Publisher'
    ids = {a['id']: a['severity'] for a in res['anti_patterns']}
    assert ids.get('critical_enrichment_current_at_publish') == 'high'
    assert ids.get('critical_enrichment_best_effort') != 'critical'
