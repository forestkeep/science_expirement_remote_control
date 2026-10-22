"""Троичное состояние: MISSING / None / value.

MISSING означает «значение не задано в этом слое» — в отличие от None,
которое является валидным явным значением. Используется в style-стеке.
"""

class _MissingType:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self):
        return "MISSING"
    def __bool__(self):
        return False

MISSING = _MissingType()