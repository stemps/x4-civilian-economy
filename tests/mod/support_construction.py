"""Native module and construction-sequence stand-ins shared by MD tests."""
from support import Component, Table, List, NIL
from md_test_runtime import PseudoValue


def module(kind, size=1):
    return Component(isclass=Table({kind: True}), numdocks=Table(dock_s=size, dock_m=size),
                     cargo=Table(capacity=Table(container=size)), numpierdocks=size)


class SequenceEntry(Table, PseudoValue):
    pass


class Sequence(List):
    def __getitem__(self, key):
        if isinstance(key, str):
            return next((entry for entry in self if entry.id == key), NIL)
        return super().__getitem__(key)


def sequence(macros):
    return Sequence(SequenceEntry(id=str(i), macro=m, exists=True) for i, m in enumerate(macros))


