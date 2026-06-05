from integration_architect_pro import Engine, defaults, form_page


def test_form_only_ui_no_free_text_instruction_and_generates_statuses_idempotency_retention():
    html = form_page()
    assert "Интеграционный инструктор v4.9.8" in html
    assert "укажите название/системы" not in html
    assert "statusesByScenario" in html
    assert "fieldsByScenario" in html
    assert "idempotencyKey:string|required|unique" in html
    assert "setField('retention'" in html
    assert "setField('statuses', sts[0])" in html
    assert "setField('final_statuses', sts[1])" in html


def gen(overrides):
    f = defaults(); f.update(overrides); return Engine().generate(f)


def test_real_case_outbox_order_kafka_from_form_choices():
    res = gen({
        'project_name':'Internet case: outbox order kafka',
        'task_type':'new_from_scratch',
        'business_goal':'Заказ создаётся, сохраняется в БД и публикуется событие для склада и доставки.',
        'business_situations':['application_or_order_creation','multi_step_business_process'],
        'main_entity':'Order','source_system':'Order Service','source_of_truth':'own_db',
        'load_profile':'medium','change_policy':['add_api','add_table','add_outbox','add_event'],
        'delivery':'at_least_once','ordering':'per_entity','orchestration':'choreography','result_model':'tracking',
        'allowed_channels':['rest','kafka','queue'],'retention':'90_days',
        'statuses':'CREATED, EVENT_PENDING, EVENT_PUBLISHED, FAILED', 'final_statuses':'EVENT_PUBLISHED, FAILED',
        'fields':'orderId:uuid|required|unique|indexed, idempotencyKey:string|required|unique, eventId:uuid|unique, correlationId:uuid|required|indexed, status:string|required|indexed, updatedAt:datetime|required',
        'systems_matrix':'Order Service | source | commerce | critical | rest,kafka | blocking | 1s\nWarehouse | consumer | warehouse | important | kafka | non_blocking | 10s',
        'process_steps':'0 | 1 | root | Создать заказ | Order Service | rest | request | order_saved | 1s | yes | none | blocking | commerce\n1 | 2 | 1 | Записать outbox | Order Service | db | order | event_pending | 1s | yes | retry | blocking | commerce\n1 | 3 | 2 | Опубликовать event | Publisher | kafka | outbox | OrderCreated | 5s | yes | dlq | non_blocking | platform',
        'error_matrix':'duplicate | consumer | non_blocking | no | dedupe by idempotencyKey/eventId | owner\ntimeout | publisher | non_blocking | yes | retry/dlq | platform'
    })
    assert res['recommended']['name'] in ['Event Choreography','Compromise: Source Outbox + Embedded/Platform Publisher']
    assert 'outbox' in [p['id'] for p in res['patterns']]
    assert 'no_idempotency' not in [a['id'] for a in res['anti_patterns']]


def test_real_case_saga_order_payment_inventory_from_form_choices():
    res = gen({
        'project_name':'Internet case: saga order payment inventory',
        'task_type':'e2e_chain', 'business_goal':'Оформить заказ через резерв склада, оплату и доставку с компенсациями.',
        'business_situations':['application_or_order_creation','multi_step_business_process','distributed_transaction_saga'],
        'main_entity':'Order','source_system':'Order API','source_of_truth':'own_db','customer_visible':'yes','money_impact':'yes',
        'load_profile':'highload','rps':'500','change_policy':['add_api','add_table','add_outbox','add_event'],
        'delivery':'business_exactly_once','ordering':'per_entity','orchestration':'orchestrator','failure_policy':'retry_compensate_manual','result_model':'tracking','step_count':'4_7','chain_depth':'multi_level','retention':'3_years',
        'statuses':'CREATED, RESERVED, PAID, DELIVERY_CREATED, COMPLETED, COMPENSATING, CANCELLED, MANUAL_REVIEW', 'final_statuses':'COMPLETED, CANCELLED, MANUAL_REVIEW',
        'fields':'orderId:uuid|required|unique|indexed, operationId:uuid|required|unique, idempotencyKey:string|required|unique, eventId:uuid|unique, correlationId:uuid|required|indexed, amount:decimal|required, status:string|required|indexed, updatedAt:datetime|required',
        'systems_matrix':'Order API | accept | commerce | critical | rest | blocking | 1s\nProcess Manager | saga | commerce | critical | queue,kafka | blocking | 30s\nInventory | reserve | warehouse | critical | queue | blocking | 5s\nPayment | authorize | payments | critical | rest,queue | blocking | 10s\nDelivery | create | logistics | important | kafka | non_blocking | 1m',
        'process_steps':'0 | 1 | root | Принять заказ | Order API | rest | request | order_created | 1s | yes | cancel | blocking | commerce\n1 | 2 | 1 | Зарезервировать товар | Inventory | queue | order | reserved | 5s | yes | release_inventory | blocking | warehouse\n1 | 3 | 2 | Авторизовать оплату | Payment | rest | payment | authorized | 10s | yes | refund/cancel_auth | blocking | payments\n1 | 4 | 3 | Создать доставку | Delivery | kafka | order | delivery_created | 30s | yes | cancel_delivery | non_blocking | logistics',
        'error_matrix':'payment_failed | Payment | blocking | no | compensate | payments\ninventory_timeout | Inventory | blocking | yes | manual_task | warehouse\nduplicate | Process Manager | blocking | no | ignore_by_idempotency | commerce'
    })
    assert res['recommended']['name'] in ['Financial Operation State Machine','Orchestrated E2E Process','Fan-out/Fan-in Orchestrated Process']
    ids=[p['id'] for p in res['patterns']]
    assert 'saga' in ids and 'outbox' in ids and 'inbox' in ids
    assert 'no_idempotency' not in [a['id'] for a in res['anti_patterns']]


def test_real_case_webhook_duplicates_from_form_choices():
    res = gen({
        'project_name':'Internet case: duplicate webhooks', 'task_type':'external_partner',
        'business_goal':'Принять webhook оплаты от партнёра, который может прийти повторно или позже.',
        'business_situations':['webhook_callback','external_api_dependency'], 'main_entity':'Payment','source_system':'Webhook API','source_of_truth':'own_db','customer_visible':'yes','money_impact':'yes',
        'load_profile':'bursty','change_policy':['add_api','add_table'],'delivery':'at_least_once','ordering':'per_entity','result_model':'callback','allowed_channels':['rest','webhook','queue'],'retention':'3_years',
        'statuses':'REQUEST_CREATED, CALLBACK_RECEIVED, CALLBACK_DUPLICATE, PROCESSED, FAILED, MANUAL_REVIEW', 'final_statuses':'PROCESSED, FAILED, MANUAL_REVIEW',
        'fields':'paymentId:uuid|required|unique|indexed, idempotencyKey:string|required|unique, externalEventId:string|required|unique, correlationId:uuid|required|indexed, status:string|required|indexed, updatedAt:datetime|required',
        'systems_matrix':'Webhook API | intake | payments | critical | rest | blocking | 1s\nInbox DB | dedupe | payments | critical | db | blocking | 1s\nWorker | apply payment | payments | critical | queue | non_blocking | 10s',
        'process_steps':'0 | 1 | root | Принять webhook | Webhook API | webhook | externalEventId | 200 accepted | 1s | yes | none | blocking | payments\n1 | 2 | 1 | Записать inbox | Inbox DB | db | event | stored_or_duplicate | 1s | yes | ignore_duplicate | blocking | payments\n1 | 3 | 2 | Обработать платеж | Worker | queue | inbox | processed | 10s | yes | dlq/manual | non_blocking | payments',
        'error_matrix':'duplicate_event | Inbox DB | non_blocking | no | ignore | payments\npoison_payload | Worker | non_blocking | yes | dlq | payments'
    })
    assert res['recommended']['name'] == 'Webhook Intake + Inbox Processing'
    assert 'inbox' in [p['id'] for p in res['patterns']]
    assert 'no_idempotency' not in [a['id'] for a in res['anti_patterns']]


def test_real_case_customer_360_and_legacy_file_and_strangler():
    customer = gen({
        'project_name':'Internet case: Customer 360', 'task_type':'new_from_scratch',
        'business_goal':'Быстро собрать карточку клиента 360 из нескольких источников с partial response.',
        'business_situations':['customer_360','api_composition','client_status_screen','highload_read'], 'main_entity':'Customer','source_system':'BFF','source_of_truth':'external',
        'customer_visible':'yes','load_profile':'highload','read_frequency':'very_high','response_time_expectation':'under_300ms','freshness_requirement':'up_to_1m','business_priority':'speed','unavailable_behavior':'partial_response','change_policy':['add_api','add_table'],'result_model':'sync','retention':'90_days',
        'statuses':'REQUESTED, PARTIAL, COMPLETE, STALE, SOURCE_UNAVAILABLE, FAILED','final_statuses':'COMPLETE, PARTIAL, STALE, FAILED',
        'fields':'customerId:uuid|required|unique|indexed, correlationId:uuid|required|indexed, status:string|required|indexed, updatedAt:datetime|required',
        'systems_matrix':'BFF | screen | product | critical | rest/cache | blocking | 300ms\nCRM | source | crm | important | rest | blocking | 500ms\nContracts | source | contracts | important | rest | blocking | 500ms\nRead Model | cache | platform | important | cache | blocking | 100ms',
        'process_steps':'0 | 1 | root | Запросить карточку | BFF | rest | customerId | response | 300ms | no | partial_response | blocking | product\n1 | 2 | 1 | Читать read model | Read Model | cache | customerId | cached_blocks | 100ms | no | stale_label | blocking | platform',
        'error_matrix':'source_timeout | BFF | non_blocking | no | partial_response | product'
    })
    assert customer['recommended']['name'] == 'BFF/API Composition with Partial Response'
    assert 'no_retention' not in [a['id'] for a in customer['anti_patterns']]

    legacy = gen({
        'project_name':'Internet case: SFTP batch', 'task_type':'legacy_integration',
        'business_goal':'Ежедневный файл партнёра: manifest, checksum, quarantine, reconciliation.',
        'business_situations':['legacy_batch','batch_processing'], 'main_entity':'FileRecord','source_system':'SFTP Gateway','source_of_truth':'external',
        'legacy':'file_only','load_profile':'low','change_policy':['add_table'],'delivery':'at_least_once','result_model':'report','allowed_channels':['sftp','file'],'forbidden_channels':['kafka'],'retention':'1_year',
        'statuses':'FILE_RECEIVED, CHECKSUM_VALIDATED, LOADED, RECONCILED, QUARANTINED, REJECTED','final_statuses':'RECONCILED, QUARANTINED, REJECTED',
        'fields':'fileId:uuid|required|unique|indexed, fileName:string|required|indexed, checksum:string|required, batchId:string|required|indexed, status:string|required|indexed, updatedAt:datetime|required',
        'systems_matrix':'SFTP Gateway | intake | platform | critical | sftp,file | non_blocking | daily\nBatch Loader | loader | data | critical | file,db | non_blocking | 1h',
        'process_steps':'0 | 1 | root | Получить файл | SFTP Gateway | sftp | file | received | 1h | yes | quarantine | non_blocking | data\n1 | 2 | 1 | Проверить checksum | Batch Loader | file | file | validated | 1h | yes | reject_report | non_blocking | data',
        'error_matrix':'checksum_failed | loader | non_blocking | no | quarantine | data'
    })
    assert legacy['recommended']['name'] == 'Batch/File Integration'

    strangler = gen({
        'project_name':'Internet case: Strangler migration','task_type':'replace_legacy',
        'business_goal':'Постепенно заменить функцию монолита через adapter, parallel run и fallback.',
        'business_situations':['migration_strangler','legacy_modernization'], 'main_entity':'Tariff','source_system':'Adapter','source_of_truth':'external',
        'legacy':'no_changes','existing_state':'legacy','compatibility':'backward','change_policy':['add_api','add_table'],'rollout':'parallel','result_model':'sync','allowed_channels':['rest'],'retention':'90_days',
        'statuses':'ROUTED_TO_LEGACY, ROUTED_TO_NEW, SHADOW_COMPARE, FALLBACK_USED, SUCCESS, FAILED','final_statuses':'SUCCESS, FALLBACK_USED, FAILED',
        'fields':'tariffId:uuid|required|unique|indexed, correlationId:uuid|required|indexed, status:string|required|indexed, updatedAt:datetime|required',
        'systems_matrix':'Monolith | legacy | legacy | critical | rest | blocking | 1s\nAdapter | routing | platform | critical | rest | blocking | 1s\nNew Service | new logic | product | critical | rest | blocking | 1s',
        'process_steps':'0 | 1 | root | Принять запрос | Adapter | rest | request | routed | 1s | yes | fallback_old | blocking | platform\n1 | 2 | 1 | Вызвать новый сервис | New Service | rest | request | result | 1s | yes | fallback_old | blocking | product\n1 | 3 | 1 | Shadow compare legacy | Adapter | rest | request | diff_report | 1s | yes | keep_legacy | non_blocking | platform',
        'error_matrix':'new_service_error | Adapter | blocking | yes | fallback_old | platform\ndiff_detected | Adapter | non_blocking | no | manual_review | product'
    })
    assert strangler['recommended']['name'] == 'Migration / Strangler Fig'
