from integration_architect_pro import Engine

BASE = dict(
    source_system='system',
    main_entity='entity',
    source_of_truth='source service',
    ownership='business owner',
    fields='entity_id | string | yes | no | id\nidempotency_key | string | no | no | dedupe\nstatus | string | yes | no | status',
    statuses='NEW,PROCESSING,DONE,FAILED',
    final_statuses='DONE,FAILED',
    retention='1_year',
    forbidden_channels=['direct_db_write'],
)

def generate(name, **form):
    return Engine().generate({**BASE, 'project_name': name, **form})

def names(res):
    return [res['recommended']['name']] + [v['name'] for v in res['variants']]

def patterns(res):
    return set(res['recommended'].get('patterns', []))

def anti_ids(res):
    return {a['id'] for a in res['anti_patterns']}


def test_public_outbox_order_event_matches_outbox_guidance():
    res = generate(
        'Public-style order event: DB update + Kafka publication',
        task_type='add_to_existing',
        business_goal='После создания заказа надёжно публиковать событие OrderCreated в Kafka для оплаты, доставки и поиска без потери событий и дублей.',
        business_situations=['event_publication', 'financial_operation'],
        source_system='Order Service', main_entity='order', source_of_truth='Order Service', ownership='Orders team',
        customer_visible='yes', money_impact='yes', load_profile='highload', rps='800', peak_factor='6',
        latency_sla='seconds', result_model='tracking', delivery='business_exactly_once', ordering='per_entity', replay='long',
        change_policy=['add_outbox'], existing_capabilities=['kafka'], allowed_channels=['rest','kafka'],
        process_steps='1 | 1 | root | Create order | Order Service | REST | order request | order persisted | 2s | no | none | blocking | Orders\n'
                      '1 | 2 | root | Publish OrderCreated | Order Service | Kafka | outbox row | event | 30s | yes | DLQ/manual | non_blocking | Orders',
    )
    assert 'Transactional Outbox' in patterns(res)
    assert 'Inbox / Idempotent Consumer' in patterns(res)
    assert res['readiness']['score'] >= 60


def test_public_saga_order_fulfillment_matches_saga_guidance():
    res = generate(
        'Public-style order fulfillment saga',
        task_type='e2e_chain',
        business_goal='Оформить заказ: резерв денег, резерв склада, доставка и финальный статус без 2PC.',
        business_situations=['application_or_order_creation','financial_operation','distributed_transaction_saga','multi_step_business_process'],
        source_system='Order Service', main_entity='order', source_of_truth='Order Service', ownership='Orders team',
        customer_visible='yes', money_impact='yes', load_profile='bursty', rps='300', peak_factor='8',
        result_model='tracking', orchestration='orchestrator', chain_depth='fanout_fanin', step_count='4_7',
        failure_policy='retry_compensate_manual', delivery='business_exactly_once', ordering='per_entity', replay='long',
        change_policy=['add_outbox'], existing_capabilities=['kafka'], allowed_channels=['rest','kafka'],
        process_steps='1 | 1 | root | Create pending order | Order Service | REST | cart | PENDING | 1s | no | reject | blocking | Orders\n'
                      '1 | 2 | root | Reserve payment | Payment | REST | orderId | PAYMENT_RESERVED | 3s | yes | release_payment | blocking | Payments\n'
                      '1 | 3 | root | Reserve stock | Inventory | REST | orderId | STOCK_RESERVED | 3s | yes | release_stock | blocking | Warehouse\n'
                      '1 | 4 | root | Create delivery | Delivery | REST | orderId | DELIVERY_CREATED | 5s | yes | cancel_delivery | blocking | Logistics\n'
                      '2 | 5 | 2,3,4 | Confirm or compensate | Order Service | internal | statuses | CONFIRMED/FAILED | 30s | yes | manual | non_blocking | Orders',
    )
    assert res['recommended']['name'] in ['Fan-out/Fan-in Orchestrated Process', 'Orchestrated E2E Process']
    assert 'Saga / Process Manager' in patterns(res)
    assert 'Transactional Outbox' in patterns(res)
    assert 'Inbox / Idempotent Consumer' in patterns(res)


def test_public_bff_composition_partial_response_is_not_downgraded_to_basic_api():
    res = generate(
        'Public-style product/customer 360 BFF',
        task_type='new_from_scratch',
        business_goal='Собрать горячий экран из нескольких сервисов быстро, с partial response и freshness labels.',
        business_situations=['api_composition','customer_360','read_model'],
        source_system='BFF', main_entity='customer_card', source_of_truth='source systems', ownership='Product team',
        customer_visible='yes', money_impact='indirect', load_profile='highload', rps='2000', peak_factor='5',
        latency_sla='subsecond', result_model='sync', read_frequency='very_high', freshness_requirement='up_to_1m',
        unavailable_behavior='partial_response', allowed_channels=['rest','cache'],
        process_steps='1 | 1 | root | Request card | Web | REST | customerId | request | 100ms | no | partial | blocking | Product\n'
                      '1 | 2 | root | Read cache/read model | BFF | cache | customerId | card parts | 100ms | no | stale label | blocking | Product\n'
                      '1 | 3 | root | Fan out to sources | BFF | REST | customerId | optional parts | 300ms | yes | partial response | blocking | Product\n'
                      '1 | 4 | root | Return composed card | BFF | REST | parts | response | 300ms | no | partial response | blocking | Product',
    )
    assert res['recommended']['name'] == 'BFF/API Composition with Partial Response'
    assert 'Fallback / Graceful Degradation' in patterns(res)
    assert 'customer_visible_without_status_model' not in anti_ids(res)
    assert 'event_without_broker' not in anti_ids(res)


def test_public_webhook_duplicate_payment_requires_inbox_and_idempotency():
    res = generate(
        'Public-style Stripe webhook duplicate payment events',
        task_type='external_partner',
        business_goal='Принимать payment webhook: событие может прийти повторно или не по порядку, нельзя дважды применить оплату.',
        business_situations=['webhook_callback','financial_operation'],
        source_system='Payment Provider', main_entity='payment_event', source_of_truth='Payment Ledger', ownership='Payments team',
        customer_visible='yes', money_impact='yes', regulatory_impact='yes', load_profile='bursty', rps='100', peak_factor='10',
        result_model='callback', failure_policy='retry_compensate_manual', delivery='business_exactly_once', ordering='per_entity', replay='audit',
        allowed_channels=['rest','queue','kafka'],
        process_steps='1 | 1 | root | Verify signature and receive webhook | Webhook Intake | REST | event | accepted | 2s | yes | inbox | non_blocking | Payments\n'
                      '1 | 2 | root | Atomically claim event id | Webhook Inbox | DB | event_id | claimed/duplicate | 1s | no | ignore duplicate | blocking | Payments\n'
                      '1 | 3 | root | Update ledger | Payment Ledger | DB | payment status | ledger updated | 2s | yes | manual | blocking | Payments\n'
                      '1 | 4 | root | Publish payment status | Payment Ledger | Kafka | PaymentUpdated | event | 30s | yes | DLQ | non_blocking | Payments',
        error_matrix='duplicate_event | intake | no | yes | ignore | Payments\nout_of_order | intake | no | yes | reconcile | Payments',
    )
    assert res['recommended']['name'] in ['Financial Operation State Machine', 'Webhook Intake + Inbox Processing']
    assert 'Inbox / Idempotent Consumer' in patterns(res)
    assert 'Webhook Intake' in ' '.join(patterns(res)) or any('Webhook Intake' in v['name'] for v in res['variants'])
    assert 'no_idempotency' not in anti_ids(res)


def test_public_sftp_bank_batch_is_file_integration_not_event_noise():
    res = generate(
        'Public-style bank H2H/SFTP batch payments',
        task_type='legacy_integration',
        business_goal='Ежедневно обмениваться платёжными файлами с банком по SFTP: пачки, квитанции, сверка, карантин битых файлов.',
        business_situations=['legacy_batch','external_partner','reconciliation'],
        source_system='ERP', main_entity='payment_file', source_of_truth='ERP', ownership='Finance',
        customer_visible='no', money_impact='yes', regulatory_impact='yes', load_profile='low', latency_sla='hours',
        result_model='tracking', failure_policy='manual', delivery='at_least_once', ordering='per_entity', replay='audit',
        legacy='file_only', allowed_channels=['sftp','file'], forbidden_channels=['rest','kafka','direct_db_write'], dwh='batch',
        process_steps='1 | 1 | root | Generate payment file | ERP | file | payments | file | 1h | yes | regenerate | non_blocking | Finance\n'
                      '1 | 2 | root | Upload to bank | ERP | SFTP | file | uploaded | 1h | yes | retry/manual | non_blocking | FinanceOps\n'
                      '1 | 3 | root | Receive ack | Bank | SFTP | ack file | accepted/rejected | 1d | yes | manual | non_blocking | FinanceOps\n'
                      '1 | 4 | root | Reconcile | Reconciliation | file/db | ack + source | report | 1d | yes | quarantine | non_blocking | FinanceOps',
    )
    assert res['recommended']['name'] == 'Batch/File Integration'
    assert 'Batch/File/SFTP' in patterns(res)
    assert 'event_without_broker' not in anti_ids(res)
    assert res['readiness']['score'] >= 85


def test_public_mission_critical_fx_migration_strangler():
    res = generate(
        'Public-style Danske FX core migration',
        task_type='replace_legacy',
        business_goal='Постепенно мигрировать mission-critical FX core из монолита в микросервисы без остановки бизнеса.',
        business_situations=['migration_strangler','financial_operation'],
        source_system='FX Monolith', main_entity='fx_trade', source_of_truth='FX Monolith', ownership='FX Core team',
        customer_visible='yes', money_impact='yes', regulatory_impact='yes', load_profile='highload', rps='600', peak_factor='4',
        latency_sla='subsecond', result_model='sync', consistency='strong', existing_state='legacy', legacy='soap_only',
        compatibility='backward_required', change_policy=['add_adapter','add_outbox'], allowed_channels=['rest','soap','kafka'],
        source_change_policy='minimal_table_only', constraint_profile='pragmatic', budget_pressure='high', deadline_pressure='tight',
        new_service_policy='platform_only', new_infra_policy='existing_only', compromise_comment='Миграция поэтапная: новый сервис нельзя внедрить сразу во все участки, нужен adapter и parallel run.',
        delivery='business_exactly_once', ordering='per_entity', replay='audit',
        process_steps='1 | 1 | root | Receive FX quote request | Client | REST | quote request | accepted | 300ms | no | reject | blocking | FX\n'
                      '1 | 2 | root | Route through anti-corruption adapter | FX Adapter | REST/SOAP | request | normalized | 200ms | yes | fallback monolith | blocking | Platform\n'
                      '1 | 3 | root | Execute legacy or new capability | FX Core | SOAP/REST | normalized | result | 500ms | yes | fallback/manual | blocking | FX\n'
                      '1 | 4 | root | Publish audit/reporting event | FX Core | Kafka | trade fact | event | 30s | yes | DLQ | non_blocking | FX',
    )
    assert 'Migration / Strangler Fig' in names(res)
    assert res['recommended']['name'] in ['Migration / Strangler Fig', 'SOAP Legacy Adapter Integration', 'Financial Operation State Machine']
    assert 'direct_db_write' not in anti_ids(res)
    assert res['readiness']['score'] >= 45
