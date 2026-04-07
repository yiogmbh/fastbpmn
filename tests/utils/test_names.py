from fastbpmn.utils.names import get_random_name


def test_get_random_name():
    assert get_random_name() in [
        "Carl",
        "Bob",
        "Kevin",
        "Phil",
        "Jerry",
        "Stuart",
        "Tom",
        "Dave",
        "Oliver",
        "Tim",
        "Jorge",
        "Lance",
    ]
