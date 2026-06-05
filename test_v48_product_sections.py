from integration_architect_pro import Engine
from test_sa_full_coverage import form as base_form


def test_product_sections_are_generated_for_complex_case():
    f = base_form()
    f.update({
        'project_name': 'v4.8 product check',
        'business_situations': ['application_or_order_creation','client_status_screen','financial_operation','multi_step_business_process','webhook_callback','legacy_integration','dwh_reporting','personal_data_exchange','regulatory_process','peak_load_process','strict_ordering_required','exactly_once_required','unstable_external_provider'],
        'task_type': 'e2e_chain',
        'money_impact': 'yes',
        'regulatory_impact': 'yes',
        'customer_visible': 'yes',
        'load_profile': 'highload',
        'rps': '1200',
        'peak_factor': '10',
        'payload_kb': '5',
        'retention_days': '30',
        'orchestration': 'orchestrator',
        'chain_depth': 'fanout_fanin',
        'step_count': '8_plus',
        'legacy': 'soap_only',
        'dwh': 'regulatory',
        'external_dependency_stability': 'unstable',
        'delivery': 'business_exactly_once',
        'ordering': 'per_entity',
        'statuses': 'CREATED,CHECKING,APPROVED,REJECTED,ERROR',
        'systems_matrix': '''Mobile | UI | product | important | rest | blocking | 300ms
API | entry | platform | critical | rest | blocking | 1s
Loan Core | core | loans | critical | internal,event | blocking | 3s
BKI | external check | partner | critical | rest,webhook | blocking | 30s
Legacy ABS | accounting | core banking | critical | soap | blocking | 10s
DWH | reporting | data | important | cdc,etl | non_blocking | 1h''',
        'process_steps': '''0 | 1 | root | Create application | API | rest | request | appId | 1s | no | none | blocking | product
1 | 2 | 1 | Start saga | Loan Core | internal | appId | state | 1s | yes | manual | blocking | loans
1 | 3 | 2 | Request BKI | BKI | rest | appId | requestId | 30s | yes | manual | blocking | partner
1 | 4 | 2 | Call legacy ABS | Legacy ABS | soap | appId | accountState | 10s | yes | compensation | blocking | core banking
2 | 5 | 3,4 | Join results | Loan Core | internal | results | decision | 1s | yes | manual | blocking | loans
2 | 6 | 5 | Publish status | Loan Core | event | decision | statusChanged | 1s | yes | dlq | non_blocking | platform
2 | 7 | 6 | Export DWH | DWH | cdc | statusChanged | report | 1h | yes | reconciliation | non_blocking | data''',
    })
    res = Engine().generate(f)
    adv = res.get('advanced', {})
    assert res['recommended']['name'] == 'Fan-out/Fan-in Orchestrated Process'
    assert adv['quality_gate']['critical_questions']
    assert any('Idempotency' in x or 'idempotency' in x for x in adv['mvp'])
    assert any('Process Manager' in x or 'Saga' in x for x in adv['production'])
    assert adv['capacity']['peak_rps'] == 12000
    assert adv['capacity']['recommended_partitions'] >= 12
    assert 'ADR-001' in adv['adr']['title']
    md = res['markdown']
    for marker in ['Quality gate требований','MVP-вариант','Production-вариант','Capacity planning lite','ADR export','Дополнительные диаграммы','Библиотека похожих шаблонов']:
        assert marker in md, marker


def test_poor_requirements_have_quality_gate_questions():
    f = base_form()
    f.update({'project_name': 'poor requirements', 'business_goal': '', 'source_of_truth': 'unclear', 'ownership': 'unclear', 'orchestration': 'unknown', 'task_type': 'e2e_chain', 'step_count': '8_plus'})
    res = Engine().generate(f)
    adv = res.get('advanced', {})
    assert adv['quality_gate']['status'] in {'blocked','risky'}
    assert any('source of truth' in x.lower() for x in adv['quality_gate']['critical_questions'])

if __name__ == '__main__':
    test_product_sections_are_generated_for_complex_case()
    print('OK test_product_sections_are_generated_for_complex_case')
    test_poor_requirements_have_quality_gate_questions()
    print('OK test_poor_requirements_have_quality_gate_questions')
    print('Passed 2 v4.8 product section tests')
