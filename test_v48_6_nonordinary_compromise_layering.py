
from integration_architect_pro import Engine


def test_compromise_publisher_is_not_top_level_for_large_e2e_fanout_flow():
    form={
      'project_name':'Кредитный договор: E2E процесс + enriched Kafka event при ограничениях',
      'business_goal':'Оформить кредитный договор через несколько систем, обогатить событие и передать downstream через единственный Kafka-контур без нового publisher-сервиса.',
      'task_type':'e2e_chain',
      'business_situations':['data_enrichment','multi_step_business_process','distributed_transaction_saga','financial_operation','external_api_dependency'],
      'load_profile':'highload','rps':'900','peak_factor':'8','latency_sla':'minutes','consistency':'eventual_controlled',
      'existing_state':'production','change_policy':['add_outbox'],
      'constraint_profile':'minimal_safe','budget_pressure':'extreme','deadline_pressure':'urgent','new_service_policy':'forbidden','new_infra_policy':'existing_only','source_change_policy':'minimal_table_only','risk_appetite':'medium',
      'compromise_comment':'Новый publisher-сервис запрещён; допустим только embedded job/platform adapter и минимальная outbox-таблица в source.',
      'existing_capabilities':['kafka'],'orchestration':'orchestrator','chain_depth':'fanout_fanin','step_count':'8_plus','failure_policy':'retry_compensate_manual','result_model':'tracking',
      'source_system':'contract_service','main_entity':'contract','source_of_truth':'main_db','ownership':'single_owner','data_volume':'large','history':'audit_log','retention':'years',
      'event_payload_intent':'enriched_event','enrichment_required':'critical','enrichment_owner_service':'profile_service','enrichment_consistency':'as_of_change',
      'delivery':'business_exactly_once','ordering':'per_entity','replay':'long','manual_recovery':'yes',
      'allowed_channels':['rest','kafka','queue'],'forbidden_channels':['direct_db_write','new_infra'],'legacy':'none','dwh':'near_realtime',
      'kafka_topology':'single_topic_only','source_has_kafka_infra':'no','enrichment_channel':'rest','security_boundary':'internal','sensitivity':'financial','auth':'service','availability':'ha','observability':'regulated','rollout':'parallel_run','testing':'contract_load_chaos',
      'systems_matrix':'contract_service|source of truth договора|Team A|critical|db/rest|blocking|99.9\nprofile_service|владелец доп. атрибутов клиента|Team B|critical|rest|blocking|99.5\nbki|внешнее БКИ|External|critical|rest|blocking|99.0\nscoring|скоринг|Risk|critical|rest|blocking|99.5\nintegration_runtime|существующий runtime/job|Platform|critical|kafka/rest|non_blocking|99.5\ntarget_service|потребитель события|Team C|critical|kafka|non_blocking|99.9\ndwh|аналитика|BI|medium|etl|non_blocking|daily',
      'process_steps':'1|1||Save contract change|contract_service|db|command|contract version|1s|no||blocking|Team A\n1|2|1|Run BKI check|bki|rest|client data|bki report|5s|yes|manual review|blocking|Risk\n1|3|1|Run scoring|scoring|rest|contract version|score result|3s|yes|manual review|blocking|Risk\n1|4|2,3|Join risk results|contract_service|db|branch results|approved/rejected|1s|yes|manual review|blocking|Team A\n1|5|4|Write pending outbox|contract_service|db|contract change|outbox row|1s|yes|manual reprocess|blocking|Team A\n1|6|5|Enrich attributes|integration_runtime|rest|outbox row|profile snapshot|3s|yes|FAILED_ENRICHMENT_REPROCESS|non_blocking|Platform\n1|7|6|Publish enriched event|integration_runtime|kafka|enriched payload|ContractChangedEnriched|5s|yes|dlq/reprocess|non_blocking|Platform\n1|8|7|Consume idempotently|target_service|kafka|event|projection update|10s|yes|dlq|non_blocking|Team C',
      'error_matrix':'profile timeout|integration_runtime|no|yes|FAILED_ENRICHMENT_REPROCESS|Platform\nkafka unavailable|integration_runtime|yes|yes|PUBLISH_RETRY_DLQ|Platform\nduplicate event|target_service|no|no|ignore by eventId|Team C\nout of order version|target_service|yes|yes|park until previous/reprocess|Team C',
      'fields':'contractId:string:required:indexed\naggregateVersion:number:required:indexed\neventId:string:required:unique\nidempotencyKey:string:required:unique\nclientSegment:string:optional:sensitive\namount:number:required:sensitive',
      'statuses':'PENDING_RISK,RISK_FAILED,APPROVED,PENDING_ENRICHMENT,ENRICHMENT_FAILED,READY_TO_PUBLISH,PUBLISHED,FAILED_REPROCESS',
      'final_statuses':'PUBLISHED,FAILED_REPROCESS,REJECTED'
    }
    result=Engine().generate(form)
    assert result['recommended']['name']=='Fan-out/Fan-in Orchestrated Process'
    names=[v['name'] for v in result['variants'][:4]]
    assert 'Compromise: Source Outbox + Embedded/Platform Publisher' in names
    tradeoffs=result['advanced']['tradeoffs']
    assert any('source-owned outbox' in x for x in tradeoffs['feasible_v1'])
    assert result['traits']['compromise_mode'] is True
    assert result['traits']['source_can_add_minimal_outbox'] is True

if __name__=='__main__':
    test_compromise_publisher_is_not_top_level_for_large_e2e_fanout_flow()
    print('OK nonordinary compromise layering')
