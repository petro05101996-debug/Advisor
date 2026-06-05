from integration_architect_pro import Engine


def test_wide_multilevel_financial_e2e_prefers_orchestrated_process_over_financial_layer():
    form={
      'project_name':'Wide financial E2E + enriched Kafka under constraints',
      'business_goal':'Change contract, run limits and compliance checks, enrich and publish final event through one Kafka using existing runtime only.',
      'task_type':'e2e_chain',
      'business_situations':['data_enrichment','multi_step_business_process','distributed_transaction_saga','financial_operation','external_api_dependency','dwh_reporting'],
      'load_profile':'highload','rps':'1500','peak_factor':'6','latency_sla':'minutes','consistency':'eventual_controlled',
      'existing_state':'production','change_policy':['add_outbox','add_status'],'existing_capabilities':['kafka','monitoring','audit'],
      'constraint_profile':'minimal_safe','budget_pressure':'extreme','deadline_pressure':'urgent','new_service_policy':'forbidden','new_infra_policy':'existing_only','source_change_policy':'minimal_table_only','risk_appetite':'low',
      'orchestration':'hybrid','chain_depth':'multi_level','step_count':'8_plus','failure_policy':'retry_compensate_manual','result_model':'tracking',
      'source_system':'contract_core','main_entity':'contract','source_of_truth':'main_db','ownership':'single_owner','data_volume':'very_large','history':'status_audit_attempts','retention':'years',
      'event_payload_intent':'enriched_event','enrichment_required':'critical','enrichment_owner_service':'profile_service','enrichment_consistency':'as_of_change',
      'delivery':'business_exactly_once','ordering':'per_entity','replay':'long','manual_recovery':'yes',
      'allowed_channels':['rest','kafka','queue'],'forbidden_channels':['new_infra','direct_db_write'],'legacy':'none','dwh':'near_realtime',
      'kafka_topology':'single_topic_only','source_has_kafka_infra':'no','enrichment_channel':'rest',
      'customer_visible':'mixed','money_impact':'yes','regulatory_impact':'yes','read_frequency':'high','change_frequency':'realtime','freshness_requirement':'up_to_1m','external_dependency_stability':'unstable',
      'security_boundary':'mixed','sensitivity':'financial','auth':'service_and_user','availability':'ha','observability':'regulated','rollout':'parallel_run','testing':'contract_load_chaos',
      'systems_matrix':'contract_core|source of truth договора|Core|critical|db/rest|blocking|99.95\nlimits|лимиты|Risk|critical|rest|blocking|99.5\nsanctions|санкционные проверки|Compliance|critical|rest|blocking|99.0\nprofile_service|атрибуты клиента|CRM|critical|rest|blocking|99.5\nintegration_runtime|существующий job/runtime|Platform|critical|rest,kafka|non_blocking|99.5\ntarget_service|потребитель|Target|critical|kafka|non_blocking|99.9\ndwh|витрина|BI|medium|etl|non_blocking|daily',
      'process_steps':'1|1||Commit contract change|contract_core|db|command|contract version|1s|no||blocking|Core\n1|2|1|Reserve/validate limits|limits|rest|contract|limit decision|2s|yes|manual review|blocking|Risk\n1|3|1|Check sanctions|sanctions|rest|client|check result|4s|yes|manual review|blocking|Compliance\n1|4|2,3|Join risk/limits|contract_core|db|partial decisions|approved/rejected|1s|yes|manual review|blocking|Core\n1|5|4|Write outbox pending event|contract_core|db|contract changed|outbox row|1s|yes|manual reprocess|blocking|Core\n1|6|5|Load enrichment profile|integration_runtime|rest|contractId/version|profile snapshot|2s|yes|ENRICHMENT_FAILED|non_blocking|Platform\n1|7|6|Publish final enriched event|integration_runtime|kafka|payload|ContractChangedEnriched|5s|yes|PUBLISH_DLQ|non_blocking|Platform\n1|8|7|Consume projection|target_service|kafka|event|projection|10s|yes|DLQ|non_blocking|Target\n1|9|7|Export to DWH|dwh|etl|event|staging|1h|yes|reconciliation|non_blocking|BI',
      'error_matrix':'limits timeout|limits|yes|yes|manual review|Risk\nsanctions timeout|sanctions|yes|yes|manual review|Compliance\nprofile timeout|integration_runtime|no|yes|ENRICHMENT_FAILED_REPROCESS|Platform\nkafka unavailable|integration_runtime|no|yes|PUBLISH_RETRY_DLQ|Platform\nduplicate event|target_service|no|no|ignore by eventId|Target\nout of order|target_service|no|yes|park/reprocess|Target\ndwh lag|dwh|no|yes|backfill/reconciliation|BI',
      'fields':'contractId:string:required:indexed\naggregateVersion:number:required:indexed\neventId:string:required:unique\nidempotencyKey:string:required:unique\ncorrelationId:string:required:indexed\nclientId:string:required:sensitive\namount:decimal:required:sensitive',
      'statuses':'NEW,LIMITS_PENDING,SANCTIONS_PENDING,APPROVED,REJECTED,PENDING_ENRICHMENT,ENRICHMENT_FAILED,READY_TO_PUBLISH,PUBLISHED,FAILED_REPROCESS',
      'final_statuses':'REJECTED,PUBLISHED,FAILED_REPROCESS'
    }
    result=Engine().generate(form)
    assert result['recommended']['name']=='Orchestrated E2E Process'
    top=[v['name'] for v in result['variants'][:3]]
    assert 'Financial Operation State Machine' in top
    assert 'Compromise: Source Outbox + Embedded/Platform Publisher' in [v['name'] for v in result['variants'][:5]]

if __name__=='__main__':
    test_wide_multilevel_financial_e2e_prefers_orchestrated_process_over_financial_layer()
    print('OK wide E2E financial layering')
