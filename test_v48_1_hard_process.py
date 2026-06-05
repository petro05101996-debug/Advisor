#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from integration_architect_pro import Engine, defaults


def test_generate_with_empty_dict_is_blocked_not_crashed():
    res = Engine().generate({})
    assert res['advanced']['quality_gate']['status'] == 'blocked'
    assert res['recommended'].get('blocked') is True
    assert 'Решение заблокировано' in res['markdown']
    assert 'Использовать Решение заблокировано' not in res['markdown']


def test_composite_architecture_is_not_raw_dict_in_markdown():
    res = Engine().generate({})
    assert "{'layer':" not in res['markdown']
    assert '### 0. Предпроектная проверка' in res['markdown']


def test_audit_critical_findings_cannot_be_green():
    f = defaults()
    f.update({
        'task_type':'audit_existing_solution',
        'project_name':'Аудит Kafka consumer',
        'current_systems_matrix':'producer | Producer | service | Team A | high | no | event | order\nconsumer | Consumer | service | Team B | critical | yes | local_db | event\ndb | Postgres | db | DBA | critical | yes | target | event',
        'current_integration_matrix':'producer | consumer | kafka | async | no | events | 1s | yes | 3 | no | no | service | prod',
        'current_process_steps':'1 | root | 1 | Read event | consumer | db | kafka | no | saved | error | no | no',
        'current_error_matrix':'db_down | consumer | technical | no | yes | log only | no | Team B | no',
        'current_problem_matrix':'duplicates | consumer | often | high | manual cleanup',
        'current_controls':['monitoring'],
    })
    res = Engine().generate(f)
    assert 'GREEN' not in res['recommended']['name']
    assert res['recommended']['score'] <= 59


def main():
    test_generate_with_empty_dict_is_blocked_not_crashed(); print('OK empty dict blocked')
    test_composite_architecture_is_not_raw_dict_in_markdown(); print('OK composite formatting')
    test_audit_critical_findings_cannot_be_green(); print('OK audit critical cap')
    print('Passed 3 v4.8.1 hard process tests')

if __name__ == '__main__':
    main()
