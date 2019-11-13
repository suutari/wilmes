from typing import Mapping, Optional

import bs4
import requests


class _Response(requests.Response):
    @property
    def soup(self) -> Optional[bs4.BeautifulSoup]: ...


class Browser:
    def request(
            self,
            method: str,
            url: str,
            headers: Mapping[str, str] = ...,
            # *args, **kwargs,
    ) -> _Response: ...

    def get(
            self,
            url: str,
            headers: Mapping[str, str] = ...,
            # *args, **kwargs,
    ) -> _Response: ...

    def post(
            self,
            url: str,
            headers: Mapping[str, str] = ...,
            # *args, **kwargs,
    ) -> _Response: ...
