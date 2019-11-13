from typing import Any, Optional, Protocol, Sequence, TypeVar, Union

from .element import Tag

_Str_T = TypeVar('_Str_T', str, bytes, covariant=True)


class _Readable(Protocol[_Str_T]):
    def read(self, n: int = ...) -> _Str_T: ...


_Str = Union[str, bytes]


class BeautifulSoup(Tag):
    def __init__(
            self,
            markup: Union[_Str, _Readable[Any]] = ...,
            features: Optional[Union[str, Sequence[str]]] = ...,
            #
            # The following parameters are unused in this code base
            # and therefore left undefined here:
            #
            # builder: Optional[...] = ...,
            # parse_only: Optional[...] = ...,
            # from_encoding: Optional[...] = ...,
            # exclude_encodings: Optional[...] = ...,
            # element_classes: Optional[...] = ...,
            # **kwargs: object,
    ) -> None: ...
