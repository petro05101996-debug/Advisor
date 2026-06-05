from integration_architect_pro import Engine, form_page


def test_shared_kafka_selective_consumer_not_outbox():
    res = Engine().generate({
        'project_name': 'Shared Kafka filter real case',
        'business_goal': 'Есть общий Kafka topic, нужны 0.2% событий по полю type. Отдельный topic запрещен, source менять нельзя, железо ограничено, пишем нужные события в Postgres.',
        'business_situations': ['shared_kafka_topic'],
        'task_type': 'add_to_existing',
        'source_system': 'Contract Service',
        'main_entity': 'ContractEvent',
        'load_profile': 'highload',
        'rps': '5000',
        'latency_sla': 'async_minutes',
        'allowed_channels': ['kafka'],
        'forbidden_channels': ['new_topic_forbidden'],
        'kafka_topology': 'single_topic_only',
        'delivery': 'at_least_once',
        'replay': 'short',
        'fields': 'eventId:string|required|unique, contractId:string|indexed, type:string|indexed',
    })
    assert res['case_classes'][0]['id'] == 'shared_topic_selective_consumer'
    assert res['recommended']['name'] == 'Shared Topic Selective Consumer + Idempotent Sink'
    assert 'selective_consumer' in res['recommended']['pattern_ids']
    assert 'filter_ratio' in ' '.join(res['structured_result']['required_controls'])


def test_aliases_customer_360_and_migration_normalized():
    r1 = Engine().generate({
        'business_goal': 'Customer 360 hot screen: карточка клиента собирает данные из 7 источников, можно частичный ответ.',
        'business_situations': ['customer_360_card'],
        'source_system': 'BFF',
        'main_entity': 'CustomerCard',
        'unavailable_behavior': 'partial_response',
        'result_model': 'sync',
        'allowed_channels': ['rest'],
    })
    assert r1['case_classes'][0]['id'] in {'bff_api_composition', 'read_model_cqrs'}
    assert 'BFF/API Composition' in r1['recommended']['name'] or 'Fast Read' in r1['recommended']['name']

    r2 = Engine().generate({
        'business_goal': 'Legacy migration modernization without big bang; нужен strangler.',
        'business_situations': ['migration_modernization'],
        'task_type': 'replace_legacy',
        'source_system': 'Legacy Core',
        'main_entity': 'Account',
        'allowed_channels': ['rest', 'cdc'],
        'rollout': 'parallel',
    })
    assert r2['case_classes'][0]['id'] == 'strangler_migration'
    assert r2['recommended']['name'] == 'Migration / Strangler Fig'


def test_read_only_bff_does_not_raise_critical_no_idempotency():
    res = Engine().generate({
        'business_goal': 'Горячий экран карточки клиента читает данные из нескольких систем. Только чтение, без mutation.',
        'business_situations': ['api_composition', 'highload_read'],
        'source_system': 'Customer BFF',
        'main_entity': 'CustomerCard',
        'result_model': 'sync',
        'unavailable_behavior': 'partial_response',
        'delivery': 'at_least_once',
        'allowed_channels': ['rest'],
        'fields': 'customerId:string|required|indexed, dataAsOf:datetime',
    })
    assert not any(a['id'] == 'no_idempotency' and a['severity'] == 'critical' for a in res['anti_patterns'])


def test_ui_version_and_export_filename_version():
    html = form_page()
    assert 'Интеграционный инструктор v4.9.8' in html
