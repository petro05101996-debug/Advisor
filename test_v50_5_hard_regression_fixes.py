from integration_architect_pro import Engine, defaults


def run(extra):
    f = defaults(); f.update(extra); return Engine().generate(f)


def names(res):
    return res['recommended']['name'], [c['id'] for c in res['case_classes']], [a['id'] for a in res['anti_patterns']]


def test_iot_command_receipt_is_not_privacy_erasure_when_negated():
    res = run({
        'project_name':'IoT command receipt telemetry',
        'business_goal':'IoT devices send command receipt acknowledgements and telemetry after firmware command delivery. Need track delivery, retries, no GDPR erasure, not a privacy deletion.',
        'task_type':'event_domain','business_situations':['data_synchronization','notification_flow'],
        'allowed_channels':['kafka','rest','queue'],'delivery':'at_least_once','result_model':'tracking',
        'fields':'deviceId:string:required:indexed\ncommandId:string:required:unique\ndeliveryId:string:required:unique\nfirmwareVersion:string:required\ntelemetryTs:datetime:required',
        'systems_matrix':'Device Gateway|source of command receipt|IoT|critical|mqtt,kafka|non_blocking|1s\nCommand Service|tracks delivery|IoT|critical|kafka|non_blocking|5s',
        'process_steps':'1|1||Receive command receipt acknowledgement|Device Gateway|kafka|command receipt|delivery event|1s|yes|dlq|non_blocking|IoT\n1|2|1|Update command delivery status|Command Service|kafka|event|status|5s|yes|reprocess|non_blocking|IoT'
    })
    assert res['recommended']['name'] != 'Privacy / Data Erasure Orchestration Pipeline'
    assert 'privacy_erasure_pipeline' not in [c['id'] for c in res['case_classes']]


def test_contract_enrichment_publish_to_only_existing_kafka_is_not_selective_consumer():
    res = run({
        'project_name':'Contract changes enriched event publisher',
        'business_goal':'Source contract service has contract changes but no Kafka infrastructure. Enrichment data lives in another REST service. Need publish enriched contract event to the only existing Kafka topic as destination.',
        'task_type':'event_domain','business_situations':['data_enrichment','one_source_many_consumers'],
        'event_payload_intent':'enriched_event','enrichment_required':'critical','enrichment_channel':'rest','enrichment_consistency':'current_at_publish',
        'kafka_topology':'single_topic_only','source_has_kafka_infra':'no','source_change_policy':'read_only','change_policy':['read_only'],
        'allowed_channels':['rest','kafka','cdc'],'delivery':'at_least_once','ordering':'per_entity','replay':'long','result_model':'notification',
        'fields':'contractId:string:required:indexed\nsourceEventId:string:required:unique\naggregateVersion:int:required\ndataAsOf:datetime:required',
        'systems_matrix':'Contract DB|source of truth|Core|critical|db|blocking|1s\nProfile REST|enrichment owner|CRM|critical|rest|blocking|2s\nIntegration Publisher|technical publisher|Platform|critical|cdc,rest,kafka|non_blocking|1m\nKafka|only existing topic destination|Platform|critical|kafka|non_blocking|1s',
        'process_steps':'1|1||Detect contract change|Integration Publisher|cdc|contract row|watermark|1m|yes|reprocess|non_blocking|Platform\n1|2|1|REST enrich|Integration Publisher|rest|contractId|profile snapshot|2s|yes|failed/reprocess|non_blocking|Platform\n1|3|2|Publish enriched event to only existing Kafka topic|Integration Publisher|kafka|payload|event|5s|yes|dlq|non_blocking|Platform'
    })
    assert res['recommended']['name'] in {'Compromise: CDC/Polling + Enrichment Export','Outbox + REST Enrichment Publisher'}
    assert res['recommended']['name'] != 'Shared Topic Selective Consumer + Idempotent Sink'
    assert 'shared_topic_selective_consumer' not in [c['id'] for c in res['case_classes']]


def test_pos_receipt_loyalty_points_is_ledger_not_privacy():
    res = run({
        'project_name':'POS receipt loyalty points ledger',
        'business_goal':'POS sales receipt events should accrue loyalty points and maintain customer points balance. Need idempotency, refund/reversal, audit and reconciliation, not GDPR erasure.',
        'task_type':'event_domain','business_situations':['financial_operation','data_synchronization'],
        'allowed_channels':['kafka','rest'],'delivery':'business_exactly_once','ordering':'per_entity','replay':'long','result_model':'tracking','money_impact':'yes',
        'fields':'receiptId:string:required:unique\noperationId:string:required:unique\ncustomerId:string:required:indexed\npointsDelta:int:required\neventId:string:required:unique',
        'systems_matrix':'POS|receipt source|Retail|critical|kafka|non_blocking|1s\nLoyalty Ledger|points balance owner|Loyalty|critical|kafka,db|blocking|1s',
        'process_steps':'1|1||Consume POS sales receipt|Loyalty Ledger|kafka|receipt|operation|1s|yes|dlq|non_blocking|Loyalty\n1|2|1|Create ledger entry and update balance|Loyalty Ledger|db|operation|balance|1s|yes|same result|blocking|Loyalty'
    })
    assert res['recommended']['name'] == 'Financial/Loyalty Ledger State Machine'
    assert 'privacy_erasure_pipeline' not in [c['id'] for c in res['case_classes']]


def test_batch_sftp_and_pricing_no_broker_forbidden_noise():
    sftp = run({
        'project_name':'Vendor nightly SFTP import','business_goal':'Vendor sends nightly CSV file by SFTP. Need manifest, checksum, staging, quarantine and ack/error file.',
        'task_type':'legacy_integration','business_situations':['batch_processing'],'legacy':'file_only','allowed_channels':['sftp','etl'],'forbidden_channels':['kafka','queue'],
        'latency_sla':'daily','delivery':'at_least_once','fields':'fileId:string:required:unique\nchecksum:string:required:unique\nbatchId:string:required:indexed',
    })
    assert sftp['recommended']['name'] == 'Batch/File Integration'
    assert 'event_target_but_broker_forbidden' not in [a['id'] for a in sftp['anti_patterns']]
    pricing = run({
        'project_name':'Pricing personalization under 100ms','business_goal':'Need price decision under 100ms using precomputed features/cache, fallback decision and audit. Not CDC modernization.',
        'task_type':'api','business_situations':['near_real_time_decision'],'latency_sla':'subsecond','response_time_expectation':'under_1s','allowed_channels':['rest'],'forbidden_channels':['kafka','queue'],
        'delivery':'at_most_once','result_model':'sync','fields':'decisionId:string:required:unique\nrequestId:string:required:indexed\nfeatureSnapshotId:string:required\nrulesVersion:string:required'
    })
    assert pricing['recommended']['name'] == 'Near Real-time Decision Flow'
    assert 'event_target_but_broker_forbidden' not in [a['id'] for a in pricing['anti_patterns']]
