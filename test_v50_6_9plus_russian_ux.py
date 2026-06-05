from integration_architect_pro import Engine, defaults


def run(**kwargs):
    f = defaults()
    f.update(kwargs)
    return Engine().generate(f)


def anti_ids(res):
    return {a['id'] for a in res['anti_patterns']}


def test_customer_360_with_loyalty_source_still_prefers_bff_not_ledger():
    res = run(
        project_name='Customer 360 support screen with Loyalty source',
        task_type='new_from_scratch',
        business_goal='Support screen Customer 360 aggregates read-only data from CRM, Orders, Billing, Tickets, Delivery, Marketing, Loyalty and Risk. Need partial response, freshness labels and per-source cache TTL. Loyalty is only a source block, not points balance mutation.',
        business_situations=['customer_360','api_composition','read_model'],
        result_model='sync',
        unavailable_behavior='partial_response',
        freshness_requirement='up_to_15m',
        read_frequency='very_high',
        delivery='at_least_once',
        allowed_channels=['rest'],
        fields='customerId:uuid|required|indexed, blockFreshness:json|required, correlationId:string|required',
        systems_matrix='CRM | profile | CRM | important | rest | blocking | 2s\nOrders | orders | Order | important | rest | blocking | 2s\nBilling | billing block | Billing | important | rest | blocking | 2s\nLoyalty | loyalty block read only | Loyalty | important | rest | blocking | 2s\nRisk | risk flags | Risk | important | rest | blocking | 2s',
        process_steps='1 | 1 | root | Request CRM | CRM | rest | id | profile | 2s | yes | partial | blocking | CRM\n1 | 2 | root | Request Loyalty block read only | Loyalty | rest | id | loyalty summary | 2s | yes | partial | blocking | Loyalty\n1 | 3 | root | Assemble Customer 360 partial response | BFF | internal | blocks | card | 1s | no | partial response | blocking | App',
    )
    assert res['recommended']['name'] == 'BFF/API Composition with Partial Response'
    assert res['traits']['operation_kind'] == 'bff_composition'
    assert res['case_classes'][0]['id'] == 'bff_api_composition'
    assert 'business_ledger' not in [c['id'] for c in res['case_classes']]
    assert 'no_idempotency' not in anti_ids(res)


def test_webhook_provider_event_id_alias_is_valid_reliability_key():
    res = run(
        project_name='Provider payment webhook',
        task_type='external_partner',
        business_goal='Payment provider sends webhook/callback. Events can be duplicated, delayed and out of order. Need signature verification, raw body, Inbox, async worker and reconciliation.',
        business_situations=['webhook_callback','external_api_dependency','exactly_once_required'],
        result_model='callback',
        delivery='business_exactly_once',
        ordering='per_entity',
        replay='long',
        customer_visible='mixed',
        money_impact='yes',
        security_boundary='external',
        allowed_channels=['webhook','queue','rest'],
        webhook_signature_required='yes',
        webhook_raw_body_preserved='yes',
        webhook_timestamp_tolerance='yes',
        webhook_reconciliation_available='yes',
        fields='providerEventId:string|required|unique, operationId:string|required|indexed, rawBody:string|required, signature:string|required, timestamp:datetime|required',
        systems_matrix='Payment Provider | webhook source | Partner | critical | webhook | non_blocking | 5s\nWebhook Gateway | intake | Platform | critical | webhook,queue | blocking | 1s\nPayment Worker | processing | Payments | critical | queue,rest | non_blocking | 1m',
        process_steps='1 | 1 | root | Verify signature and save raw event to Inbox | Webhook Gateway | webhook | rawBody | ack | 1s | yes | inbox retry | non_blocking | Platform\n1 | 2 | 1 | Process event idempotently | Payment Worker | queue | providerEventId | payment state | 1m | yes | DLQ/manual | non_blocking | Payments',
        error_matrix='duplicate | Webhook Gateway | non_blocking | no | return same result | Platform\nout_of_order | Payment Worker | non_blocking | yes | state/version check | Payments\npoison | Payment Worker | non_blocking | yes | DLQ/manual | Payments',
    )
    assert res['recommended']['name'] == 'Webhook Intake + Inbox Processing'
    assert 'no_idempotency' not in anti_ids(res)


def test_direct_db_write_policy_not_false_high_for_own_projection_sink():
    res = run(
        project_name='Shared Kafka topic to own Postgres projection',
        task_type='add_to_existing',
        business_goal='Consumer reads from shared Kafka topic, filters relevant contract events and writes only to our own Postgres projection/sink. Owners do not allow a new topic.',
        business_situations=['shared_topic_selective_consumer','data_synchronization'],
        kafka_topology='single_topic_only',
        allowed_channels=['kafka','rest'],
        forbidden_channels=['new_topic_forbidden'],
        delivery='at_least_once',
        replay='long',
        result_model='notification',
        fields='eventId:string|required|unique, contractId:string|required|indexed, sourceEventId:string|required|unique',
        systems_matrix='Shared Kafka | source topic | Platform | critical | kafka | non_blocking | 1s\nOur Consumer | filter | Our team | critical | kafka | non_blocking | 1s\nOur Projection DB | own sink | Our team | important | db | non_blocking | 1s',
        process_steps='1 | 1 | root | Consume from shared topic and filter | Our Consumer | kafka | event | accepted event | 1s | yes | DLQ | non_blocking | Our team\n1 | 2 | 1 | Upsert into own projection DB | Our Consumer | db | event | projection row | 1s | yes | retry/DLQ | non_blocking | Our team',
    )
    assert res['recommended']['name'] == 'Shared Topic Selective Consumer + Idempotent Sink'
    assert 'direct_db_write' not in anti_ids(res)
    # Missing explicit direct_db_write ban can be a medium policy note elsewhere, but must not block this own-sink case as чужая БД.
    assert res['production_gate']['level'] in {'GREEN', 'YELLOW', 'AMBER'}


def test_retention_blocker_is_specific_not_generic_phrase():
    res = run(
        project_name='DWH prod offload retention missing',
        task_type='dwh_analytics',
        business_goal='Production DB grows by terabytes per year. DWH takes daily data. Need archive/offload, watermark, backfill and reconciliation.',
        business_situations=['dwh_reporting','batch_processing'],
        data_volume='very_large',
        retention='not_defined',
        delivery='at_least_once',
        replay='rebuild',
        allowed_channels=['cdc','etl'],
        fields='recordId:string|required|indexed, watermark:string|required, checksum:string|required',
        systems_matrix='Core DB | source | Core | critical | cdc | non_blocking | daily\nDWH | analytics | Data | critical | etl | non_blocking | daily',
        process_steps='1 | 1 | root | Extract by watermark | Core DB | cdc | watermark | staging | daily | yes | retry | non_blocking | Data\n1 | 2 | 1 | Reconcile and archive | DWH | etl | staging | report | daily | yes | reconciliation | non_blocking | Data',
    )
    titles = [a['title'] for a in res['anti_patterns']]
    assert any('DWH/archive' in t for t in titles)
    assert 'Нет retention для больших данных' not in titles
