from integration_architect_pro import Engine, defaults


def generate(**kwargs):
    form = defaults()
    form.update(kwargs)
    return Engine().generate(form)


def test_active_active_financial_write_is_red_not_green():
    result = generate(
        project_name='Active-active multi-region balance writes',
        business_goal='Два региона active-active принимают операции по балансу одного клиента. Возможен split-brain и double spend.',
        business_situations=['financial_operation', 'active_active_financial_write'],
        money_impact='yes',
        sensitivity='financial',
        consistency='strong_on_write',
        allowed_channels=['rest', 'kafka'],
        delivery='business_exactly_once',
        ordering='per_entity',
        load_profile='highload',
        rps='1000',
        fields='operationId:uuid|required|unique, accountId:uuid|required|indexed, amount:decimal|required',
    )
    assert result['structured_result']['case_class'] == 'active_active_financial_write'
    assert result['recommended']['name'] == 'Financial Operation State Machine'
    assert result['production_gate']['level'] == 'RED'
    assert any(a['id'] == 'active_active_financial_write' and a['severity'] == 'critical' for a in result['anti_patterns'])


def test_iot_telemetry_stream_is_not_ranked_as_dwh_top_level():
    result = generate(
        project_name='IoT telemetry stream',
        business_goal='100k devices send telemetry events. Need realtime alerting, out-of-order events handling, and DWH only as downstream consumer.',
        business_situations=['highload_stream_ingestion'],
        load_profile='highload',
        rps='100000',
        allowed_channels=['kafka'],
        result_model='notification',
        data_volume='very_large',
        dwh='near_realtime',
        delivery='at_least_once',
        ordering='per_entity',
        replay='long',
        retention='1_year',
        fields='eventId:string|required|unique, deviceId:string|required|indexed, eventTime:datetime|required',
    )
    assert result['structured_result']['case_class'] == 'highload_stream_ingestion'
    assert result['recommended']['name'] == 'Highload Stream Ingestion / Stream Processing'
    assert result['recommended']['name'] != 'Data Pipeline / DWH'


def test_multi_tenant_noisy_neighbor_is_explicit_warning():
    result = generate(
        project_name='Multi-tenant shared consumer pool',
        business_goal='200 tenants use one Kafka consumer pool. One large tenant creates noisy neighbor and lag for others.',
        business_situations=['multi_tenant_noisy_neighbor', 'shared_topic_selective_consumer'],
        load_profile='highload',
        rps='5000',
        allowed_channels=['kafka'],
        kafka_topology='single_topic_only',
        forbidden_channels=['new_topic_forbidden'],
        delivery='at_least_once',
        ordering='per_entity',
        replay='long',
        fields='eventId:string|required|unique, tenantId:string|required|indexed, entityId:string|required|indexed',
    )
    assert result['structured_result']['case_class'] == 'multi_tenant_noisy_neighbor'
    assert result['recommended']['name'] == 'Shared Topic Selective Consumer + Idempotent Sink'
    assert any(a['id'] == 'multi_tenant_noisy_neighbor' for a in result['anti_patterns'])
    assert result['production_gate']['level'] in {'YELLOW', 'RED'}


def test_privacy_legal_hold_is_called_out():
    result = generate(
        project_name='Удаление ПДн с legal hold',
        business_goal='Пользователь просит удалить ПДн, данные ушли в Kafka, DWH и object storage. Часть нельзя удалить из-за legal hold / retention exception.',
        business_situations=['privacy_erasure'],
        regulatory_impact='yes',
        sensitivity='pii',
        data_volume='large',
        allowed_channels=['rest', 'kafka'],
        dwh='regulatory',
        replay='audit',
        retention='not_defined',
        fields='erasureRequestId:uuid|required|unique, subjectId:uuid|required|indexed',
    )
    assert result['structured_result']['case_class'] == 'privacy_erasure_pipeline'
    assert any(a['id'] == 'privacy_legal_hold_exception' for a in result['anti_patterns'])
    assert result['production_gate']['level'] in {'YELLOW', 'RED'}
