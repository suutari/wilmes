from typing import Iterable

from bs4.element import Tag


def delete_subelements(
        element: Tag,
        delete: Iterable[str],
) -> None:
    for selector in delete or []:
        tag_to_clean = element.select_one(selector)
        if tag_to_clean:
            tag_to_clean.replace_with('')


def stringify_contents(element: Tag) -> str:
    return '\n'.join(stringify_subelements(element))


def stringify_subelements(element: Tag) -> Iterable[str]:
    strings = (str(x) for x in element)
    return (x for x in strings if x.strip())
