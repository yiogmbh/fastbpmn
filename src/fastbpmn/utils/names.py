import random


def get_random_name() -> str:

    names = [
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

    return random.choice(names)
