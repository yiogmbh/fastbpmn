from fastbpmn.task import TaskProperties


def test_task_properties_lock_duration():

    values = {
        "topic": "test-topic",
        "retries": 3,
        "process_definition_key": "test-process-definition-key",
        "handler": lambda x: x,
    }

    props_1 = TaskProperties(**values)
    props_2 = TaskProperties(**(values | {"lock_duration": 1000}))
    props_3 = TaskProperties(**(values | {"lock_duration": None}))

    assert props_1.lock_duration == 300_000
    assert props_2.lock_duration == 1000
    assert props_3.lock_duration == 300_000
