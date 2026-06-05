from integration_architect_pro import Engine, defaults


def run_case(**overrides):
    f = defaults()
    f.update(overrides)
    return Engine().generate(f)


def test_cb_loan_purpose_schema_change_prefers_regulatory_impact_analysis():
    res = run_case(
        project_name='ЦБ изменил модель цели займа',
        task_type='add_to_existing',
        business_goal='Раньше у кредита была одна цель займа, теперь ЦБ решил, что у кредита может быть несколько целей займа. Нужно оценить изменение модели данных, API, DWH, совместимость потребителей, миграцию и backfill.',
        business_situations=['regulatory_process','dwh_reporting','data_synchronization'],
        regulatory_impact='yes',
        dwh='regulatory',
        result_model='report',
        fields='loanId:string|required|indexed, purpose:string|deprecated, purposes:array|required, schemaVersion:int|required, migrationRunId:string|required',
        systems_matrix='Loan Core | владелец кредита | Core | critical | rest,event | blocking | 1s\nDWH | отчётность | Data | critical | cdc,etl | non_blocking | daily\nExternal Report | регуляторная отчётность | Compliance | critical | file,api | non_blocking | daily',
        process_steps='0 | 1 | root | Изменить модель кредита | Loan Core | db/api | old purpose | purposes + schemaVersion | 1d | yes | rollback migration | blocking | Core\n1 | 2 | 1 | Мигрировать историю | DWH | etl | old rows | migrated rows | 1d | yes | backfill | non_blocking | Data',
        allowed_channels=['rest','cdc','etl','sftp'],
        delivery='at_least_once',
    )
    assert res['recommended']['name'] == 'Regulatory Data Model Change Impact Analysis'
    assert res['structured_result']['case_class'] == 'regulatory_schema_change'
    assert 'schemaVersion' in str(res['structured_result']['required_controls'])


def test_prod_db_tb_growth_prefers_dwh_offload_not_plain_batch_file():
    res = run_case(
        project_name='Prod DB растёт TB/year, нужна разгрузка в DWH',
        task_type='dwh_analytics',
        business_goal='Продовая БД распухает на терабайты в год. ДВХ забирает данные раз в день. Нужно разгрузить prod, retention/archive, watermark, сверка, backfill и cold storage.',
        business_situations=['dwh_reporting','batch_processing','data_synchronization'],
        regulatory_impact='no',
        dwh='batch',
        data_volume='very_large',
        retention='not_defined',
        result_model='report',
        allowed_channels=['cdc','etl','sftp'],
        systems_matrix='Prod DB | источник | Core | critical | cdc | non_blocking | daily\nDWH | аналитика | Data | important | etl,sftp | non_blocking | daily\nObject Storage | архив | Data | important | sftp | non_blocking | daily',
        process_steps='0 | 1 | root | Снять инкремент | Prod DB | cdc | watermark | staging | daily | yes | retry offset | non_blocking | Data\n1 | 2 | 1 | Архивировать старые данные | Object Storage | etl/sftp | partition | archive snapshot | daily | yes | reconciliation | non_blocking | Data',
        fields='recordId:string|required|indexed, updatedAt:datetime|required, watermark:string|required, checksum:string|required, snapshotId:string|required',
        delivery='at_least_once',
        replay='rebuild',
    )
    assert res['recommended']['name'] == 'Data Pipeline / DWH'
    assert res['structured_result']['case_class'] == 'dwh_pipeline'
    assert any('Watermark/offset' in x for x in res['contracts']['dwh'])
    assert any('Retention/archive' in x for x in res['contracts']['dwh'])


def test_payment_webhook_is_top_level_even_when_money_operation_exists():
    res = run_case(
        project_name='Payment provider webhook',
        task_type='external_partner',
        business_goal='Провайдер платежей присылает webhook/callback о статусе платежа, возможны дубли, out-of-order, retry provider и сверка с provider API.',
        business_situations=['webhook_callback','financial_operation','external_api_dependency'],
        result_model='callback',
        money_impact='yes',
        regulatory_impact='yes',
        security_boundary='external',
        sensitivity='financial',
        webhook_signature_required='yes',
        webhook_raw_body_preserved='yes',
        webhook_timestamp_tolerance='yes',
        webhook_reconciliation_available='yes',
        allowed_channels=['webhook','queue','rest','kafka'],
        delivery='at_least_once',
        systems_matrix='Payment Provider | внешний webhook | Partner | critical | webhook | non_blocking | 3s\nPayment API | приём | Payments | critical | rest,queue | non_blocking | 1s',
        process_steps='0 | 1 | root | Принять webhook и быстро ACK | Payment Provider | webhook | rawBody+signature | ack | 3s | yes | reject invalid | non_blocking | Payments\n1 | 2 | 1 | Обновить operation state | Payment API | queue/db | provider_event_id | operationStatus | 10s | yes | retry/dlq | non_blocking | Payments',
        fields='provider_event_id:string|required|unique, delivery_id:string|required|indexed, rawBody:string|required, signature:string|required, timestamp:datetime|required, operationId:string|required|indexed, aggregateVersion:int|required',
    )
    assert res['recommended']['name'] == 'Webhook Intake + Inbox Processing'
    assert res['structured_result']['case_class'] == 'webhook_intake'
    assert any('rawBody' in x for x in res['contracts']['security'])


def test_bff_partial_response_is_not_red_only_for_fanout():
    res = run_case(
        project_name='Customer 360 BFF',
        task_type='new_from_scratch',
        business_goal='Оператор открывает карточку клиента из CRM, ABS и KYC. Допустим partial response, разные freshness по блокам, timeout per source и fallback.',
        business_situations=['multi_source_aggregation','many_sources_one_consumer','highload_read','external_api_dependency'],
        read_frequency='high',
        response_time_expectation='under_1s',
        freshness_requirement='up_to_15m',
        unavailable_behavior='partial_response',
        orchestration='hybrid',
        chain_depth='fanout_fanin',
        step_count='4_7',
        result_model='sync',
        allowed_channels=['rest','queue'],
        delivery='at_least_once',
        systems_matrix='CRM | профиль | CRM | important | rest | blocking | 2s\nABS | счета | ABS | critical | rest | blocking | 2s\nKYC | проверки | Compliance | critical | rest | blocking | 3s',
        process_steps='1 | 1 | root | Запросить CRM | CRM | rest | id | profile | 2s | yes | stale block | blocking | CRM\n1 | 2 | root | Запросить ABS | ABS | rest | id | accounts | 2s | yes | hide block | blocking | ABS\n1 | 3 | root | Запросить KYC | KYC | rest | id | kyc | 3s | yes | manual review marker | blocking | KYC\n1 | 4 | root | Собрать partial response | BFF | internal | parts | card | 1s | no | partial | blocking | App',
        fields='requestId:string|required, correlationId:string|required, clientId:string|required|indexed',
    )
    assert res['recommended']['name'] == 'BFF/API Composition with Partial Response'
    assert res['production_gate']['level'] in {'GREEN','YELLOW'}
    assert 'RED' != res['production_gate']['level']
