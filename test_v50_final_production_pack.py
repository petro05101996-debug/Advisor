import json, zipfile
from pathlib import Path
import integration_architect_pro as m


def base(**kw):
    f=m.defaults(); f.update({
        'project_name':'v5 production regression',
        'business_goal':'Есть общий Kafka topic, source менять нельзя, отдельный topic запрещён, нужно фильтровать 1% событий и писать их в Postgres.',
        'business_situations':['shared_kafka_topic'],
        'load_profile':'highload','rps':'1200','peak_factor':'5','latency_sla':'async_minutes','consistency':'eventual_ok',
        'existing_state':'production','source_change_policy':'forbidden','new_infra_policy':'existing_only',
        'allowed_channels':['kafka','rest'],'forbidden_channels':['new_topic_forbidden'],
        'delivery':'at_least_once','replay':'manual','main_entity':'ContractEvent',
        'source_system':'Contract Service','target_system':'Analytics DB',
        'fields':'eventId:uuid|required|unique, contractId:uuid|required|indexed, eventType:string|required, updatedAt:datetime|required',
        'systems_matrix':'Contract Service | source | Contract Team | critical | Kafka | async | 60s\nAnalytics DB | sink | Data Team | important | SQL | async | 60s',
        'process_steps':'1 | 1 | root | Read shared topic | Consumer | Kafka | event | filtered event | 60s | yes | retry | non_blocking | Integration Team\n1 | 2 | 1 | Write accepted event | Consumer | SQL | filtered event | row | 5s | yes | dlq/manual | non_blocking | Integration Team',
        'error_matrix':'poison_message | Consumer | non_blocking | yes | DLQ | Integration Team',
        'observability':'full','testing':'full','rollout':'canary'
    }); f.update(kw); return f


def gen(**kw):
    return m.Engine().generate(base(**kw))


def test_v50_generates_document_bundle_zip(tmp_path):
    res=gen(); zname, prefix, files=m.make_document_bundle(res,'abcdef123456',1)
    assert zname.endswith('.zip')
    zp=m.OUT_DIR/zname
    assert zp.exists()
    with zipfile.ZipFile(zp) as z:
        names=set(z.namelist())
    assert {'integration_design.md','ADR.md','api_contract.yaml','event_contract.json','test_cases.md','risk_register.md','checklist.md','structured_result.json'} <= names


def test_openapi_contract_contains_core_headers():
    y=m.make_openapi_yaml(gen())
    assert 'openapi: 3.0.3' in y and 'Idempotency-Key' in y and 'Correlation-Id' in y


def test_event_contract_contains_selective_consumer_when_needed():
    contract=json.loads(m.make_event_contract_json(gen()))
    assert 'selectiveConsumer' in contract
    assert 'filter_ratio' in contract['selectiveConsumer']['metrics']


def test_risk_register_is_markdown_table():
    md=m.make_risk_register_md(gen())
    assert '| Риск | Severity | Где | Что сделать | Owner |' in md


def test_test_cases_pack_has_negative_cases():
    md=m.make_test_cases_md(gen())
    for text in ['duplicate request/event','DLQ/quarantine replay','out-of-order event','reconciliation mismatch']:
        assert text in md


def test_checklist_has_production_items():
    md=m.make_checklist_md(gen())
    assert 'Production Checklist' in md and 'load/stress/failover tests' in md and 'rollback/canary/feature-toggle plan' in md


def test_adr_export_has_context_decision_alternatives():
    md=m.make_adr_md(gen())
    assert '## Context' in md and '## Decision' in md and '## Alternatives' in md and '## Rollback' in md


def test_template_library_has_at_least_fifteen_templates():
    res=gen()
    assert len(res['advanced']['templates']) >= 15


def test_markdown_contains_production_gate_section():
    md=gen()['markdown']
    assert '## 12A. Production gate' in md and '## 12B. Self-check результата' in md


def test_structured_result_contains_gate_and_controls():
    sr=gen()['structured_result']
    assert sr['gate']['level'] in ['GREEN','YELLOW','AMBER','RED']
    assert sr['required_controls']


def test_shared_topic_still_selects_selective_consumer():
    res=gen()
    assert res['case_classes'][0]['id']=='shared_topic_selective_consumer'
    assert 'selective_consumer' in res['recommended']['pattern_ids']


def test_bundle_structured_json_is_valid():
    res=gen(); zname,_,_=m.make_document_bundle(res,'feedface0000',2)
    with zipfile.ZipFile(m.OUT_DIR/zname) as z:
        data=json.loads(z.read('structured_result.json').decode('utf-8'))
    assert data['recommended']['name']


def test_customer360_read_only_does_not_require_idempotency_blocker():
    res=gen(business_goal='Карточка клиента customer 360 из 7 систем, только чтение, partial response, SLA 1s.', business_situations=['customer_360_card','highload_read'], result_model='query', allowed_channels=['rest'], forbidden_channels=[], source_change_policy='read_only', kafka_topology='no_kafka')
    blockers=res['production_gate']['blocking_gaps']
    assert not any('idempot' in b.lower() for b in blockers)


def test_enrichment_contract_appears_only_for_enrichment_case():
    plain=gen(enrichment_required='none', event_payload_intent='domain_fact')
    assert 'Event enrichment before Kafka publish' not in plain['markdown'] or 'shared Kafka' in plain['markdown']
    enriched=gen(business_goal='Договоры нужно дообогатить через REST и отправить в Kafka; source без Kafka.', business_situations=['data_enrichment'], enrichment_required='required', enrichment_channel='rest', source_has_kafka_infra='no', event_payload_intent='enriched_event')
    assert 'Event enrichment before Kafka publish' in enriched['advanced']['templates']


def test_api_bundle_file_names_are_stable():
    _,_,files=m.make_document_bundle(gen(),'abc123',3)
    assert files[0]=='integration_design.md' and 'api_contract.yaml' in files


def test_production_gate_before_prod_has_six_controls():
    controls=gen()['production_gate']['required_before_prod']
    assert len(controls) >= 6


def test_capacity_notes_exist():
    cap=gen()['advanced']['capacity']
    assert cap['peak_rps'] > 0 and cap['recommended_partitions'] >= 3 and cap['notes']


def test_self_check_mentions_contracts_and_tests():
    md=gen()['markdown']
    assert 'contracts сгенерированы' in md and 'test cases сформированы' in md


def test_current_solution_audit_still_available():
    f=base(task_type='audit_existing_solution')
    res=m.Engine().generate(f)
    assert 'Вердикт аудита' in res['recommended']['name']


def test_webhook_security_blocker_when_missing_signature():
    res=gen(business_goal='Внешний провайдер шлёт webhook с платежным статусом, есть дубли и retry.', business_situations=['webhook_callback','financial_operation'], money_impact='yes', webhook_signature_required='no', webhook_raw_body_preserved='no')
    assert any('Webhook security' in b for b in res['production_gate']['blocking_gaps'])


def test_regulatory_impact_analysis_present():
    res=gen(business_goal='ЦБ изменил модель: у кредита теперь несколько целей займа.', business_situations=['regulatory_change'], regulatory_impact='yes')
    assert any('API contracts' in x for x in res['advanced']['impact_analysis'])


def test_dwh_retention_impact_present():
    res=gen(business_goal='DWH забирает данные, prod БД раздувается на терабайты raw payload.', business_situations=['dwh_retention'], dwh='regulatory', data_volume='very_large')
    assert any('Storage/retention' in x for x in res['advanced']['impact_analysis'])


def test_form_page_exposes_zip_download_wording_after_result_function_compiles():
    assert 'Скачать пакет документов ZIP' in m.result_page(gen(),'rid','file.md','bundle.zip')


def test_parse_post_preserves_output_choices():
    body='task_type=e2e_chain&preset_name=x&business_goal=test&simple_outputs=adr'
    f=m.parse_post(body)
    assert f['preset_name']=='x'


def test_normalization_understands_russian_source_forbidden():
    f=m.normalize_form({'business_goal':'Источник менять нельзя, отдельный топик запрещён, общий Kafka topic', 'business_situations':[]})
    assert f['source_change_policy']=='forbidden'
    assert 'shared_topic_selective_consumer' in f['business_situations']


def test_quality_gate_and_bundle_do_not_crash_for_minimal_form():
    res=m.Engine().generate({'business_goal':'Простая REST интеграция', 'business_situations':['external_api_dependency']})
    zname,_,_=m.make_document_bundle(res,'min000',1)
    assert (m.OUT_DIR/zname).exists()
