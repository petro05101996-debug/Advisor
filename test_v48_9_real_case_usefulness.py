import integration_architect_pro as m


def base(**overrides):
    f = m.defaults()
    f.update(overrides)
    return f


def test_external_partner_login_password_is_not_misclassified_as_event_enrichment():
    f = base(
        project_name='External BKI API login/password',
        task_type='external_partner',
        business_goal='External BKI API uses login/password; store secrets safely, rotate password, avoid credential leakage, handle lockouts and rate limits.',
        business_situations=['external_api_dependency','personal_data_exchange','regulatory_process','unstable_external_provider'],
        source_system='Credit Report Service',
        systems_matrix='Credit Report Service | owner | core | critical | REST | sync/async | 3s\nBKI API | bureau | external | critical | REST | limited | 5s\nVault | secrets | platform | critical | API | sync | 1s',
        process_steps='1 | 1 | root | Validate request | Credit Report Service | REST | request | requestId | 1s | no | reject | blocking | core\n2 | 2 | 1 | Call BKI API | Credit Report Service | REST | request | bureau response | 5s | yes | manual review | blocking | core\n3 | 3 | 2 | Store status and audit | Credit Report Service | SQL | response | status | 1s | yes | retry | non_blocking | core',
        fields='requestId:uuid|required|unique, clientId:uuid|required|sensitive, idempotencyKey:string|required|unique, correlationId:uuid|required',
        main_entity='CreditReportRequest',
        source_of_truth='external',
        ownership='single',
        delivery='business_exactly_once',
        allowed_channels=['rest','queue'],
        dwh='no',
        kafka_topology='no_kafka',
        enrichment_required='none',
        enrichment_channel='none',
        event_payload_intent='domain_fact',
        sensitivity='financial',
        observability='full',
        rps='50',
        peak_factor='5',
        load_profile='medium',
    )
    res = m.Engine().generate(f)
    md = res['markdown']
    assert res['recommended']['name'] in ['External API Adapter with Resilience', 'Async Job / Heavy Processing Flow']
    assert 'Enrichment contracts: owner of source event' not in md
    assert 'Event enrichment before Kafka publish' not in md
    assert 'Single Kafka topic + REST enrichment' not in md
    assert 'Vault' in md or 'secrets management' in md
