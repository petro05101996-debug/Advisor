from integration_architect_pro import Engine, defaults


def run(**kwargs):
    f = defaults()
    f.update(kwargs)
    return Engine().generate(f)


def anti_ids(res):
    return {a['id'] for a in res['anti_patterns']}


def test_regulatory_schema_change_is_top_level_not_generic_outbox():
    res = run(
        project_name='ЦБ: несколько целей займа',
        task_type='add_to_existing',
        business_goal='Регулятор изменил модель кредита: раньше одна цель займа, теперь у кредита может быть несколько целей. Нужно оценить БД, API, DWH и потребителей.',
        business_situations=['regulatory_process'],
        regulatory_impact='yes',
        allowed_channels=['rest','kafka','cdc','etl'],
        delivery='at_least_once',
        fields='creditId:uuid|required|indexed, purposeCode:string, purposeCodes:json|required, schemaVersion:int|required',
        systems_matrix='Credit Core | кредит | Core | critical | rest,kafka | blocking | 1s\nDWH | отчетность | Data | critical | cdc,etl | non_blocking | daily',
        process_steps='1 | 1 | root | Изменить модель | Credit Core | db/api | credit | versioned model | 1d | yes | rollback | blocking | Core\n1 | 2 | 1 | Backfill DWH | DWH | etl | credit | report | 1d | yes | reconciliation | non_blocking | Data',
    )
    assert res['recommended']['name'] == 'Regulatory Data Model Change Impact Analysis'
    assert res['case_classes'][0]['id'] == 'regulatory_schema_change'
    assert 'Regulatory Data Model Change Impact Analysis' in res['markdown']


def test_dwh_offload_uses_watermark_not_generic_idempotency_blocker():
    res = run(
        project_name='DWH забирает данные, prod DB растёт',
        task_type='dwh_analytics',
        business_goal='Production база растёт на терабайты, DWH забирает данные раз в день. Нужно вынести историю/архив и не блокировать core.',
        business_situations=['dwh_reporting','batch_processing'],
        dwh='batch',
        allowed_channels=['cdc','etl','sftp'],
        delivery='at_least_once',
        replay='rebuild',
        fields='recordId:uuid|required|indexed, snapshotId:string|required, watermark:string|required, checksum:string|required',
        systems_matrix='Core DB | источник | Core | critical | cdc | non_blocking | daily\nDWH | отчётность | Data | important | etl | non_blocking | daily',
        process_steps='1 | 1 | root | Extract delta | Core DB | cdc | watermark | staging | 1h | yes | retry | non_blocking | Data\n1 | 2 | 1 | Reconcile | DWH | etl | staging | report | 1h | yes | reconciliation | non_blocking | Data',
    )
    assert res['recommended']['name'] == 'Data Pipeline / DWH'
    assert res['traits']['operation_kind'] == 'dwh_offload'
    assert 'no_idempotency' not in anti_ids(res)


def test_customer_360_read_only_prefers_bff_and_no_idempotency_blocker():
    res = run(
        project_name='Customer 360 с partial response',
        task_type='new_from_scratch',
        business_goal='Оператор открывает карточку клиента из CRM, ABS и KYC; один источник может тормозить, нужен частичный ответ.',
        business_situations=['multi_source_aggregation','many_sources_one_consumer','highload_read','external_api_dependency'],
        result_model='sync',
        orchestration='hybrid',
        chain_depth='fanout_fanin',
        step_count='4_7',
        unavailable_behavior='partial_response',
        freshness_requirement='up_to_15m',
        delivery='at_least_once',
        allowed_channels=['rest','queue'],
        fields='customerId:uuid|required|indexed, correlationId:uuid|required, blockFreshness:json|required',
        systems_matrix='CRM | profile | CRM | important | rest | blocking | 2s\nABS | accounts | ABS | important | rest | blocking | 2s\nKYC | checks | Compliance | important | rest | blocking | 3s',
        process_steps='1 | 1 | root | CRM | CRM | rest | id | profile | 2s | yes | partial | blocking | CRM\n1 | 2 | root | ABS | ABS | rest | id | accounts | 2s | yes | partial | blocking | ABS\n1 | 3 | root | KYC | KYC | rest | id | kyc | 3s | yes | partial | blocking | KYC\n2 | 4 | 1,2,3 | Build card | BFF | internal | parts | card | 1s | no | partial | blocking | App',
    )
    assert res['recommended']['name'] == 'BFF/API Composition with Partial Response'
    assert res['traits']['operation_kind'] == 'bff_composition'
    assert 'no_idempotency' not in anti_ids(res)


def test_legacy_soap_replacement_prefers_strangler_not_soap_adapter():
    res = run(
        project_name='Legacy SOAP replacement',
        task_type='replace_legacy',
        business_goal='Постепенно заменить SOAP/file legacy без big bang, нужен parallel run и rollback.',
        business_situations=['migration_or_strangler','legacy_integration'],
        legacy='soap_only',
        compatibility='parallel',
        rollout='parallel',
        allowed_channels=['rest','soap','cdc','etl'],
        delivery='at_least_once',
        fields='entityId:uuid|required|indexed, migrationRunId:string|required, checksum:string|required',
        systems_matrix='Facade | новый вход | Platform | critical | rest | blocking | 1s\nLegacy | старая система | Legacy | critical | soap | blocking | 5s',
        process_steps='1 | 1 | root | Route request | Facade | rest | request | response | 1s | yes | rollback | blocking | Platform\n1 | 2 | 1 | Call legacy | Legacy | soap | request | legacy response | 5s | yes | fallback | blocking | Legacy',
    )
    assert res['recommended']['name'] == 'Migration / Strangler Fig'
    assert 'SOAP Legacy Adapter Integration' in [v['name'] for v in res['variants'][:6]]


def test_unstable_partner_api_prefers_external_adapter_controls():
    res = run(
        project_name='External API with rate limits',
        task_type='external_partner',
        business_goal='Внешний партнёр часто тормозит, есть rate limit и lockout; нужно безопасно получать отчёт и хранить аудит.',
        business_situations=['external_api_dependency','unstable_external_provider','personal_data_exchange'],
        external_dependency_stability='limited',
        result_model='tracking',
        delivery='business_exactly_once',
        allowed_channels=['rest','queue'],
        fields='requestId:uuid|required|unique, partnerRequestId:string|unique, correlationId:uuid|required, clientId:uuid|required|sensitive',
        systems_matrix='Core | инициатор | Core | critical | rest | blocking | 1s\nPartner API | внешний отчёт | External | critical | rest | limited | 5s',
        process_steps='1 | 1 | root | Validate | Core | rest | request | requestId | 1s | no | reject | blocking | Core\n1 | 2 | 1 | Call partner | Partner API | rest | requestId | report | 5s | yes | manual review | blocking | Core',
    )
    assert res['recommended']['name'] in {'External API Adapter with Resilience','Async Job / Heavy Processing Flow'}
    assert 'External API Adapter with Resilience' in [v['name'] for v in res['variants'][:3]]


def test_webhook_payment_prefers_inbox_intake():
    res = run(
        project_name='Duplicate payment webhook',
        task_type='external_partner',
        business_goal='Партнёр присылает webhook оплаты, он может прийти повторно, позже или не по порядку.',
        business_situations=['webhook_callback','external_api_dependency'],
        result_model='callback',
        money_impact='yes',
        delivery='at_least_once',
        allowed_channels=['rest','webhook','queue'],
        webhook_signature_required='yes',
        webhook_raw_body_preserved='yes',
        webhook_timestamp_tolerance='yes',
        webhook_reconciliation_available='yes',
        fields='paymentId:uuid|required|indexed, externalEventId:string|required|unique, deliveryId:string|unique, correlationId:uuid|required, rawBody:json|required, signature:string|required',
        systems_matrix='Webhook API | intake | Payments | critical | webhook | blocking | 1s\nWorker | apply payment | Payments | critical | queue | non_blocking | 10s',
        process_steps='1 | 1 | root | Accept webhook | Webhook API | webhook | deliveryId | 200 | 1s | yes | inbox | blocking | Payments\n1 | 2 | 1 | Apply state | Worker | queue | inbox | processed | 10s | yes | dlq/manual | non_blocking | Payments',
    )
    assert res['recommended']['name'] == 'Webhook Intake + Inbox Processing'
    assert res['traits']['operation_kind'] == 'webhook_event_intake'
