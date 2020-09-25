from typing import Iterable

from bs4.element import Tag


def stringify_contents(element: Tag) -> str:
    return '\n'.join(stringify_subelements(element))


def stringify_subelements(element: Tag) -> Iterable[str]:
    strings = (str(x) for x in element)
    return (x for x in strings if x.strip())
