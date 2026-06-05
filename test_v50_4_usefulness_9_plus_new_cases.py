# -*- coding: utf-8 -*-
from integration_architect_pro import Engine, defaults, privacy_erasure_signal


def run(**kw):
    f=defaults(); f.update(kw); return Engine().generate(f)


def test_iot_command_receipt_is_not_privacy_erasure():
    f=defaults(); f.update(
        project_name='IoT firmware command receipt',
        business_goal='IoT device sends command receipt for firmware update, telemetry and delivery acknowledgement; keep evidence for audit and retention.',
        business_situations=['highload_write_stream','one_source_many_consumers'],
        allowed_channels=['kafka','queue'], result_model='notification', delivery='at_least_once',
        fields='deviceId:string|required|indexed, commandId:string|required|unique, receiptId:string|required|unique, firmwareVersion:string|required'
    )
    assert privacy_erasure_signal(f) is False
    res=Engine().generate(f)
    assert res['structured_result']['case_class'] != 'privacy_erasure_pipeline'


def test_loyalty_pos_receipt_is_not_privacy_erasure():
    f=defaults(); f.update(
        project_name='Loyalty points from POS receipts',
        business_goal='POS receipt from retail purchase creates loyalty points ledger event; receipt is purchase evidence, not deletion evidence.',
        business_situations=['financial_operation','one_source_many_consumers'],
        money_impact='indirect', allowed_channels=['kafka'], result_model='notification', delivery='at_least_once',
        fields='receiptId:string|required|unique, customerId:string|required|indexed, points:int|required'
    )
    assert privacy_erasure_signal(f) is False
    res=Engine().generate(f)
    assert res['structured_result']['case_class'] != 'privacy_erasure_pipeline'


def test_healthcare_lab_results_webhook_intake_wins_over_generic_saga():
    res=run(
        project_name='Healthcare lab results webhook',
        business_goal='External lab sends webhook callback with lab result. Need signature validation, raw body, quick ACK, async processing, dedupe, status transition and reconciliation API.',
        business_situations=['webhook_callback','regulatory_process','multi_step_business_process','personal_data_exchange'],
        result_model='callback', sensitivity='high', security_boundary='external', delivery='at_least_once',
        allowed_channels=['webhook','queue','rest'], webhook_signature_required='yes', webhook_raw_body_preserved='yes',
        fields='externalEventId:string|required|unique, patientId:string|required|sensitive, resultId:string|required|unique',
        systems_matrix='Lab Provider | external | Lab | critical | webhook | non_blocking | 3s\nInbox | intake | Platform | critical | queue | non_blocking | 1m\nEHR | target | Health | critical | rest | blocking | 5s',
        process_steps='1 | 1 | root | Receive webhook | Inbox | webhook | raw event | ack | 3s | yes | quarantine | non_blocking | Platform\n1 | 2 | 1 | Update result | EHR | rest | event | status | 5s | yes | manual review | blocking | Health'
    )
    assert res['structured_result']['case_class']=='webhook_intake'
    assert res['recommended']['name']=='Webhook Intake + Inbox Processing'
    assert 'Webhook security не подтверждён' not in '\n'.join(res['production_gate']['blocking_gaps'])


def test_vendor_sftp_nightly_import_is_batch_file_not_external_adapter():
    res=run(
        project_name='Vendor nightly SFTP import', task_type='external_partner',
        business_goal='Vendor drops nightly CSV file to SFTP. Need manifest, checksum, staging, quarantine, partial reject report, ack file and reprocess by file id.',
        business_situations=['batch_processing','external_api_dependency'], latency_sla='daily', result_model='report',
        allowed_channels=['sftp','etl'], legacy='file_only', delivery='at_least_once',
        source_system='Vendor SFTP', main_entity='VendorFile', source_of_truth='external', ownership='external',
        systems_matrix='Vendor SFTP | source | Vendor | critical | sftp | non_blocking | 1d\nLoader | loader | Data | important | etl | non_blocking | 1d',
        process_steps='1 | 1 | root | Receive file | Vendor SFTP | sftp | csv | fileId | 1d | yes | quarantine | non_blocking | Data',
        fields='fileId:string|required|unique, checksum:string|required|unique, rowHash:string|required|indexed'
    )
    assert res['structured_result']['case_class']=='batch_file_exchange'
    assert res['recommended']['name']=='Batch/File Integration'


def test_data_lake_cdc_schema_drift_is_dwh_pipeline_not_cdc_modernization():
    res=run(
        project_name='Data Lake CDC schema drift', task_type='dwh_analytics',
        business_goal='Debezium CDC feeds Data Lake bronze/silver/gold zones; need schema drift policy, lineage, data quality gates, watermark and backfill.',
        business_situations=['dwh_reporting','data_synchronization'], dwh='near_realtime', allowed_channels=['cdc','etl'],
        delivery='at_least_once', replay='rebuild', source_system='Debezium', main_entity='LakeRecord', source_of_truth='external', ownership='single',
        systems_matrix='Debezium | cdc source | Platform | critical | cdc | non_blocking | 5s\nData Lake | target | Data | critical | etl | non_blocking | 1m',
        process_steps='1 | 1 | root | Ingest CDC | Debezium | cdc | lsn | bronze | 5s | yes | retry | non_blocking | Data',
        fields='sourceLsn:string|required|unique, snapshotId:string|required, checksum:string|required'
    )
    assert res['traits']['operation_kind']=='dwh_offload'
    assert res['structured_result']['case_class']=='dwh_pipeline'
    assert res['recommended']['name']=='Data Pipeline / DWH'


def test_pricing_personalization_under_100ms_is_near_realtime_not_cdc():
    res=run(
        project_name='Pricing personalization under 100ms',
        business_goal='Need decision under 100ms using precomputed features, fallback decision, model/rules version and audit; CDC may update feature cache but is not the top-level solution.',
        business_situations=['near_real_time_decision','highload_read','external_api_dependency'],
        latency_sla='subsecond', response_time_expectation='under_100ms', result_model='sync', allowed_channels=['rest','kafka','cdc'],
        source_system='Pricing API', main_entity='PricingDecision', source_of_truth='own_db', ownership='single',
        systems_matrix='Pricing API | decision | Pricing | critical | rest | blocking | 100ms\nFeature Cache | feature store | ML | critical | rest | blocking | 30ms',
        process_steps='1 | 1 | root | Make decision | Pricing API | rest | request | decision | 100ms | no | fallback | blocking | Pricing',
        fields='decisionId:string|required|unique, requestId:string|required|unique, featureSnapshotId:string|required, modelVersion:string|required'
    )
    assert res['traits']['operation_kind']=='near_real_time_decision'
    assert res['structured_result']['case_class']=='near_real_time_decision'
    assert res['recommended']['name']=='Near Real-time Decision Flow'


def test_yellow_or_red_gate_always_has_explicit_blockers():
    res=run(
        project_name='Webhook without security',
        business_goal='External webhook callback updates a regulated status but signature and raw body are unknown.',
        business_situations=['webhook_callback','regulatory_process'], result_model='callback', security_boundary='external', sensitivity='financial',
        allowed_channels=['webhook'], delivery='at_least_once', webhook_signature_required='unknown', webhook_raw_body_preserved='unknown',
        fields='externalEventId:string|required|unique, status:string|required'
    )
    assert res['production_gate']['level'] in {'RED','YELLOW','AMBER'}
    assert res['production_gate']['blocking_gaps']


def test_compromise_matrix_and_sa_questions_are_present():
    res=run(
        project_name='Contract event enrichment compromise',
        business_goal='Contract changes must be published to Kafka enriched via REST. Source has no Kafka infra, new service is too expensive, single Kafka topic only.',
        business_situations=['data_enrichment','one_source_many_consumers'], event_payload_intent='enriched_event', enrichment_required='critical', enrichment_channel='rest',
        kafka_topology='single_topic_only', source_has_kafka_infra='no', new_service_policy='reuse_existing_runtime', constraint_profile='pragmatic',
        change_policy=['add_outbox','add_event'], source_change_policy='minimal_table_only', allowed_channels=['rest','kafka'], delivery='at_least_once',
        fields='contractId:string|required|indexed, eventId:string|required|unique, aggregateVersion:int|required'
    )
    assert len(res['advanced']['compromise_matrix'])==3
    questions='\n'.join(res['advanced']['quality_gate']['critical_questions'])
    assert 'business owner события' in questions
    assert 'главным результатом' in questions
