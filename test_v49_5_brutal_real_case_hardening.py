from integration_architect_pro import Engine, defaults


def gen(overrides):
    f = defaults()
    f.update(overrides)
    return Engine().generate(f)


def ids(res):
    return [a['id'] for a in res['anti_patterns']]


def test_brutal_webhook_financial_requires_signature_or_raw_body_control():
    res = gen({
        'project_name':'Brutal real case: financial webhook without signature control',
        'task_type':'external_partner',
        'business_goal':'Партнёр присылает webhook оплаты. Событие может прийти повторно, поздно или с подменённым payload.',
        'business_situations':['webhook_callback','external_api_dependency','financial_operation'],
        'main_entity':'Payment','source_system':'Webhook API','source_of_truth':'own_db',
        'customer_visible':'yes','money_impact':'yes','sensitivity':'financial','auth':'partner',
        'load_profile':'bursty','change_policy':['add_api','add_table'],
        'delivery':'at_least_once','ordering':'per_entity','result_model':'callback',
        'allowed_channels':['rest','webhook','queue'],'retention':'3_years',
        'statuses':'REQUEST_CREATED, CALLBACK_RECEIVED, CALLBACK_DUPLICATE, PROCESSED, FAILED, MANUAL_REVIEW',
        'final_statuses':'PROCESSED, FAILED, MANUAL_REVIEW',
        'fields':'paymentId:uuid|required|unique|indexed, externalEventId:string|required|unique, amount:decimal|required, status:string|required|indexed',
        'systems_matrix':'Partner | webhook source | partner | critical | webhook | non_blocking | 5s\nWebhook API | intake | payments | critical | webhook,queue | blocking | 1s',
        'process_steps':'0 | 1 | root | Принять webhook | Webhook API | webhook | externalEventId | 200 accepted | 1s | yes | ignore_duplicate | blocking | payments\n1 | 2 | 1 | Записать inbox | Inbox DB | db | event | stored_or_duplicate | 1s | yes | ignore_duplicate | blocking | payments',
        'error_matrix':'duplicate_event | Inbox DB | non_blocking | no | ignore | payments\ninvalid_signature | Webhook API | blocking | no | reject_4xx | payments'
    })
    assert res['recommended']['name'] in ['Webhook Intake + Inbox Processing', 'Financial Operation State Machine']
    assert 'webhook_signature_not_defined' in ids(res)
    assert 'no_idempotency' not in ids(res)


def test_brutal_event_target_but_broker_forbidden_is_critical_not_ready():
    res = gen({
        'project_name':'Brutal real case: event target but Kafka forbidden',
        'task_type':'new_from_scratch',
        'business_goal':'Создать заказ и передать событие нескольким потребителям, но форма запрещает Kafka и очереди.',
        'business_situations':['application_or_order_creation','one_source_many_consumers'],
        'main_entity':'Order','source_system':'Order Service','source_of_truth':'own_db',
        'load_profile':'medium','change_policy':['add_event'],
        'allowed_channels':['rest'],'forbidden_channels':['kafka','direct_db_write'],
        'kafka_topology':'no_kafka','delivery':'at_least_once','ordering':'per_entity','result_model':'tracking','retention':'90_days',
        'fields':'orderId:uuid|required|unique, eventId:uuid|unique, correlationId:uuid|required',
        'systems_matrix':'Order Service | source | commerce | critical | rest | blocking | 1s\nWarehouse | consumer | warehouse | critical | rest | non_blocking | 10s',
        'process_steps':'0 | 1 | root | Создать заказ | Order Service | rest | request | saved | 1s | yes | retry | blocking | commerce\n1 | 2 | 1 | Уведомить потребителей | Warehouse | event | order | received | 10s | yes | retry | non_blocking | warehouse',
        'error_matrix':'consumer_timeout | Warehouse | non_blocking | yes | retry/manual | warehouse'
    })
    assert 'event_target_but_broker_forbidden' in ids(res)
    assert res['readiness']['confidence_level'] in ['low','medium']
    assert res['advanced']['quality_gate']['status'] == 'risky'


def test_brutal_regulatory_change_has_full_impact_analysis():
    res = gen({
        'project_name':'Brutal real case: ЦБ multiple loan purposes',
        'task_type':'add_to_existing',
        'business_goal':'Регулятор изменил модель кредита: раньше одна цель займа, теперь несколько целей. Нужно не сломать API, events, DWH, отчёты и legacy consumers.',
        'business_situations':['regulatory_process','data_synchronization','dwh_reporting','personal_data_exchange'],
        'main_entity':'Loan','source_system':'Loan Core','source_of_truth':'own_db',
        'regulatory_impact':'yes','sensitivity':'financial','load_profile':'medium','existing_state':'production',
        'change_policy':['add_api','add_event','add_table'],'existing_capabilities':['rest_api','kafka','dwh','monitoring','audit'],
        'delivery':'at_least_once','ordering':'per_entity','result_model':'report','allowed_channels':['rest','kafka','etl'],'retention':'5_years',
        'fields':'loanId:uuid|required|unique, loanPurpose:string|required, loanPurposes:array|required, eventVersion:string|required, correlationId:uuid|required|indexed, operationId:uuid|required|unique',
        'systems_matrix':'Loan Core | source | loans | critical | rest,kafka | blocking | 1s\nDWH | reporting | data | important | etl | non_blocking | daily\nConsumers | consumers | external | important | kafka | non_blocking | 1m',
        'process_steps':'0 | 1 | root | Обновить модель кредита | Loan Core | rest | loan | saved | 1s | yes | rollback | blocking | loans\n1 | 2 | 1 | Опубликовать событие | Loan Core | kafka | loan | event | 1s | yes | dlq | non_blocking | loans\n1 | 3 | 1 | Выгрузить DWH | DWH | etl | loan | report | daily | yes | reconciliation | non_blocking | data',
        'error_matrix':'legacy_consumer_error | Consumers | non_blocking | yes | dlq | external'
    })
    impact = '\n'.join(res['advanced']['impact_analysis'])
    assert 'DB/model' in impact
    assert 'API contracts' in impact
    assert 'Events/Kafka' in impact
    assert 'DWH/reports' in impact
    assert 'Legacy consumers' in impact
    assert 'Testing' in impact
    assert 'Impact analysis' in res['markdown']


def test_brutal_dwh_raw_payload_storage_requires_archive_uri_not_prod_bloat():
    res = gen({
        'project_name':'Brutal real case: DWH raw BKI payload bloat',
        'task_type':'dwh_analytics',
        'business_goal':'Prod DB хранит raw payload кредитных отчётов БКИ, за год растёт больше 1ТБ, DWH забирает данные раз в день. Нужно не раздувать OLTP.',
        'business_situations':['dwh_reporting','batch_processing','personal_data_exchange'],
        'main_entity':'CreditReport','source_system':'BKI Adapter','source_of_truth':'external',
        'regulatory_impact':'yes','sensitivity':'financial','load_profile':'medium','data_volume':'very_large',
        'change_policy':['add_table'],'delivery':'at_least_once','ordering':'per_entity','result_model':'report','allowed_channels':['etl','sftp'],'dwh':'batch','retention':'5_years',
        'fields':'reportId:uuid|required|unique, clientId:uuid|required|indexed|sensitive, batchId:string|required|indexed, checksum:string|required, archiveUri:string|required, status:string|required|indexed',
        'systems_matrix':'BKI Adapter | intake | credit | critical | rest,file | blocking | 10s\nObject Storage | raw archive | platform | critical | file | non_blocking | 1m\nDWH | analytics | data | important | etl | non_blocking | daily',
        'process_steps':'0 | 1 | root | Получить отчёт БКИ | BKI Adapter | rest | request | raw_payload | 10s | yes | retry/manual | blocking | credit\n1 | 2 | 1 | Сохранить raw payload в archive storage | Object Storage | file | payload | archiveUri | 1m | yes | retry/manual | non_blocking | platform\n1 | 3 | 2 | Передать metadata в DWH | DWH | etl | archiveUri,metadata | loaded | daily | yes | reconciliation | non_blocking | data',
        'error_matrix':'dwh_load_failed | DWH | non_blocking | yes | replay_by_batch | data'
    })
    impact = '\n'.join(res['advanced']['impact_analysis'])
    assert 'raw payload' in impact
    assert 'archiveUri' in impact
    assert 'Purge/archive' in impact
    assert 'Reconciliation' in impact
