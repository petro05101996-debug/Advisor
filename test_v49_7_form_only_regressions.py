#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression checks for production-hardening fixes found during full audit."""
from integration_architect_pro import Engine, defaults


def base_form():
    f = defaults()
    f.update({
        'source_system':'Source Service',
        'main_entity':'Entity',
        'source_of_truth':'source',
        'ownership':'single_owner',
        'fields':'entityId:uuid|required|indexed, eventId:uuid|required|unique'
    })
    return f


def test_form_only_db_kafka_dual_write_detects_outbox_without_matrices():
    f = base_form()
    f.update({
        'business_situations':['one_source_many_consumers'],
        'allowed_channels':['rest','kafka'],
        'change_policy':['add_event','add_outbox'],
        'result_model':'notification',
        'delivery':'at_least_once',
        'ordering':'per_entity'
    })
    res = Engine().generate(f)
    assert res['case_classes'][0]['id'] == 'dual_write_db_broker'
    assert res['recommended']['name'] == 'Event-driven + Transactional Outbox'
    assert 'outbox' in res['recommended']['pattern_ids']
    assert res['production_gate']['level'] in {'GREEN','YELLOW'}


def test_financial_external_webhook_without_signature_is_red_even_if_financial_core_wins():
    f = base_form()
    f.update({
        'business_situations':['webhook_callback','financial_operation'],
        'allowed_channels':['webhook','queue'],
        'result_model':'callback',
        'security_boundary':'external',
        'sensitivity':'financial',
        'money_impact':'yes',
        'delivery':'at_least_once'
    })
    res = Engine().generate(f)
    assert 'webhook_intake' in {x['id'] for x in res['case_classes']}
    assert res['production_gate']['level'] == 'RED'
    assert any('Webhook security' in x for x in res['production_gate']['blocking_gaps'])


def test_source_read_only_event_request_is_non_invasive_not_basic_api():
    f = base_form()
    f.update({
        'existing_state':'production',
        'business_situations':['one_source_many_consumers'],
        'source_change_policy':'forbidden',
        'allowed_channels':['rest','kafka'],
        'change_policy':[],
        'result_model':'notification',
        'delivery':'at_least_once'
    })
    res = Engine().generate(f)
    assert res['case_classes'][0]['id'] == 'non_invasive_extension'
    assert res['recommended']['name'] == 'Non-invasive Existing Process Extension'


def test_thin_event_current_at_publish_with_markers_is_not_business_conflict():
    f = base_form()
    f.update({
        'fields':'entityId:uuid|required|indexed, eventId:uuid|required|unique, dataAsOf:datetime|required, sourceEventId:string|required, aggregateVersion:int|required',
        'business_situations':['webhook_callback','data_enrichment','external_api_dependency'],
        'result_model':'callback',
        'allowed_channels':['webhook','rest','queue'],
        'event_payload_intent':'thin_event',
        'enrichment_required':'critical',
        'enrichment_channel':'rest',
        'enrichment_consistency':'current_at_publish',
        'security_boundary':'external',
        'sensitivity':'financial',
        'money_impact':'yes',
        'webhook_signature_required':'yes',
        'webhook_raw_body_preserved':'yes',
        'webhook_timestamp_tolerance':'yes',
        'webhook_reconciliation_available':'yes',
        'delivery':'at_least_once'
    })
    res = Engine().generate(f)
    assert not any(a['id'].startswith('business_conflict') for a in res['anti_patterns'])
    assert res['recommended']['name'] in {'Outbox + REST Enrichment Publisher','Webhook Intake + Inbox Processing'}
