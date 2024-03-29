from typing import (
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
    overload,
)

_T = TypeVar('_T')
_MatchAgainst = Union[str, bool]  # incomplete (e.g. Callable, Iterable, ...)


class SoupStrainer:
    ...


class ResultSet(List[_T]):
    def __init__(
            self,
            source: SoupStrainer,
            result: Iterable[_T] = ...,
    ) -> None: ...


class PageElement:
    ...


class Tag(PageElement):
    name: str

    next_element: Optional[Tag]
    next_sibling: Optional[Tag]
    parent: Optional[Tag]
    previous_element: Optional[Tag]
    previous_sibling: Optional[Tag]

    @overload
    def get(self, key: str) -> Optional[str]: ...

    @overload
    def get(self, key: str, default: _T) -> Union[str, _T]: ...

    def __setitem__(self, key: str, value: str) -> None: ...

    def get_text(
            self,
            separator: str = ...,
            strip: bool = ...,
            types: Optional[Sequence[type]] = ...
    ) -> str: ...

    @property
    def text(self) -> str: ...

    def find(
            self,
            name: Optional[str] = ...,
            attrs: Mapping[str, _MatchAgainst] = ...,
            recursive: bool = ...,
            text: Optional[str] = ...,
            **kwargs: _MatchAgainst,
    ) -> Optional['Tag']: ...

    def find_all(
            self,
            name: str = ...,
            attrs: Mapping[str, _MatchAgainst] = ...,
            recursive: bool = ...,
            text: Optional[str] = ...,
            limit: Optional[int] = ...,
            **kwargs: _MatchAgainst,
    ) -> ResultSet['Tag']: ...

    def find_next(
            self,
            name: Optional[str] = ...,
            attrs: Mapping[str, _MatchAgainst] = ...,
            text: Optional[str] = ...,
            limit: Optional[int] = ...,
            **kwargs: _MatchAgainst,
    ) -> Optional['Tag']: ...

    def find_previous(
            self,
            name: Optional[str] = ...,
            attrs: Mapping[str, _MatchAgainst] = ...,
            text: Optional[str] = ...,
            limit: Optional[int] = ...,
            **kwargs: _MatchAgainst,
    ) -> Optional['Tag']: ...

    def select(
            self,
            selector: str,
            # namespaces=None, limit=None, **kwargs,
    ) -> List['Tag']: ...

    def select_one(
            self,
            selector: str,
            # namespaces=None, **kwargs,
    ) -> Optional['Tag']: ...

    def replace_with(self, replace_with: Union[str, 'Tag']) -> 'Tag': ...

    def __iter__(self) -> Iterator['Tag']: ...
