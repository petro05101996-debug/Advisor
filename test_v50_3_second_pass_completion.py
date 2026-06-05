from integration_architect_pro import Engine, defaults


def run_case(**overrides):
    f = defaults()
    f.update(overrides)
    return Engine().generate(f)


def test_privacy_erasure_is_first_class_not_generic_sync_or_saga():
    res = run_case(
        project_name='GDPR erasure / удаление ПДн во всех системах',
        task_type='add_to_existing',
        business_goal='Пользователь запросил удаление персональных данных: CRM, Orders, Analytics, Search и backups. Нужны identity validation, legal hold, retention exception, per-system erase commands, receipts/evidence, audit, retry/re-drive и manual escalation.',
        business_situations=['personal_data_exchange','regulatory_process','privacy_erasure','long_running_process'],
        regulatory_impact='yes',
        sensitivity='pii',
        security_boundary='mixed',
        result_model='tracking',
        orchestration='orchestrator',
        chain_depth='multi_level',
        step_count='4_7',
        failure_policy='retry_compensate_manual',
        allowed_channels=['rest','queue'],
        delivery='at_least_once',
        replay='yes',
        manual_recovery='yes',
        retention='5_years',
        systems_matrix='Privacy API | прием DSAR | Legal | critical | rest | blocking | 1d\nCRM | ПДн | CRM | critical | rest | non_blocking | 1d\nOrders | заказы | Core | critical | rest | non_blocking | 1d\nSearch | индекс | Search | important | queue | non_blocking | 1d\nAnalytics | витрина | Data | important | queue | non_blocking | 1d',
        process_steps='0 | 1 | root | Validate subject and legal hold | Privacy API | rest | subjectId | decision | 1d | yes | manual review | blocking | Legal\n1 | 2 | 1 | Send erase command to systems | Privacy API | queue/rest | erasureRequestId | receipts | 7d | yes | escalate | non_blocking | Legal',
        fields='erasureRequestId:string|required|unique, subjectId:string|required|indexed|sensitive, legalHoldDecisionId:string|required, receiptId:string|required, evidenceUri:string|required',
    )
    assert res['recommended']['name'] == 'Privacy / Data Erasure Orchestration Pipeline'
    assert res['structured_result']['case_class'] == 'privacy_erasure_pipeline'
    assert any('Legal hold' in x for x in res['contracts']['privacy'])
    assert any('Receipt/evidence' in x for x in res['contracts']['privacy'])


def test_cdc_legacy_modernization_is_not_dwh_when_goal_is_operational_projection():
    res = run_case(
        project_name='Legacy contracts CDC modernization',
        task_type='add_to_existing',
        business_goal='Legacy core нельзя менять. Нужно через CDC/WAL/LSN снимать изменения договоров, публиковать operational event stream в Kafka и строить read model/projection для нового сервиса. Это не DWH/offload.',
        business_situations=['legacy_integration','cdc_legacy_modernization','data_synchronization','one_source_many_consumers'],
        source_change_policy='forbidden',
        existing_capabilities=['cdc','monitoring'],
        legacy='db_replica_only',
        dwh='no',
        allowed_channels=['cdc','kafka','queue'],
        delivery='at_least_once',
        replay='rebuild',
        result_model='event',
        systems_matrix='Legacy Core DB | source | Core | critical | cdc | non_blocking | 5s\nKafka | operational event stream | Platform | critical | kafka | non_blocking | 5s\nContract Read Model | projection | New | critical | kafka | non_blocking | 5s',
        process_steps='0 | 1 | root | Read WAL/LSN changes | Legacy Core DB | cdc | lsn | change record | 5s | yes | gap detection | non_blocking | Platform\n1 | 2 | 1 | Publish operational event | Kafka | kafka | change record | event | 5s | yes | dlq/replay | non_blocking | Platform\n1 | 3 | 2 | Update projection | Contract Read Model | kafka/db | event | projection | 5s | yes | rebuild | non_blocking | New',
        fields='sourceLsn:string|required|unique, contractId:string|required|indexed, aggregateVersion:int|required, projectionVersion:int|required, operation:string|required',
    )
    assert res['recommended']['name'] == 'CDC Legacy Modernization / Operational Projection'
    assert res['structured_result']['case_class'] == 'cdc_legacy_modernization'
    assert any('LSN/watermark' in x for x in res['contracts']['cdc'])
    assert res['structured_result']['case_class'] != 'dwh_pipeline'


def test_near_realtime_decision_beats_financial_state_machine_when_latency_is_core():
    res = run_case(
        project_name='Near-real-time fraud decision',
        task_type='new_from_scratch',
        business_goal='Нужно принять fraud decision за 200 мс: precomputed features/cache, bounded latency per dependency, fallback decision, circuit breaker, audit of feature snapshot and final outcome.',
        business_situations=['near_real_time_decision','financial_operation','data_enrichment'],
        money_impact='yes',
        sensitivity='financial',
        response_time_expectation='under_1s',
        latency_sla='subsecond',
        freshness_requirement='up_to_1m',
        unavailable_behavior='fallback_value',
        orchestration='single',
        chain_depth='single_level',
        step_count='2_3',
        result_model='sync',
        allowed_channels=['rest','queue'],
        delivery='business_exactly_once',
        replay='yes',
        systems_matrix='Fraud API | decision | Risk | critical | rest | blocking | 200ms\nFeature Store | precomputed features | ML | critical | rest/cache | blocking | 50ms',
        process_steps='0 | 1 | root | Load feature snapshot | Feature Store | rest/cache | clientId | feature_snapshot_id | 50ms | yes | fallback decision | blocking | ML\n1 | 2 | 1 | Make fraud decision | Fraud API | rules/model | features | decision | 150ms | yes | manual review | blocking | Risk',
        fields='decisionId:string|required|unique, requestId:string|required, featureSnapshotId:string|required, rulesVersion:string|required, outcome:string|required',
    )
    assert res['recommended']['name'] == 'Near Real-time Decision Flow'
    assert res['structured_result']['case_class'] == 'near_real_time_decision'
    assert any('feature_snapshot_id' in x for x in res['contracts']['decision'])


def test_last_item_reservation_does_not_get_false_dwh_retention_blocker():
    res = run_case(
        project_name='Last item reservation + payment',
        task_type='e2e_chain',
        business_goal='Последний товар: резерв, платеж, expiry, доставка, компенсация, idempotency. Нужна защита от double booking и понятные статусы.',
        business_situations=['financial_operation','distributed_transaction_saga','application_or_order_creation'],
        money_impact='yes',
        data_volume='large',
        history='none',
        retention='not_defined',
        dwh='no',
        replay='no',
        orchestration='orchestrator',
        chain_depth='multi_level',
        step_count='4_7',
        failure_policy='retry_compensate_manual',
        allowed_channels=['rest','queue','kafka'],
        delivery='business_exactly_once',
        result_model='tracking',
        manual_recovery='yes',
        systems_matrix='Order API | order | Core | critical | rest | blocking | 1s\nInventory | reserve | Stock | critical | rest | blocking | 1s\nPayment | charge | Pay | critical | rest | blocking | 3s',
        process_steps='0 | 1 | root | Create order | Order API | rest | request | order | 1s | yes | cancel | blocking | Core\n1 | 2 | 1 | Reserve last item | Inventory | rest | sku | reservation | 1s | yes | release reservation | blocking | Stock\n2 | 3 | 2 | Charge payment | Payment | rest | amount | payment | 3s | yes | refund | blocking | Pay',
        fields='orderId:string|required|unique, idempotencyKey:string|required|unique, reservationId:string|required, paymentId:string|required, status:string|required',
    )
    titles = [x['title'] for x in res['anti_patterns']]
    assert 'Нет retention для больших данных' not in titles
    assert res['structured_result']['case_class'] == 'saga_orchestration'
