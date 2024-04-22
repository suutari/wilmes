from typing import Any, Mapping, Optional

import bs4
import requests


class _Response(requests.Response):
    @property
    def soup(self) -> Optional[bs4.BeautifulSoup]: ...


class Browser:
    def __init__(
            self,
            # TODO: Replace Any with Session
            session: Optional[Any] = ...,
            soup_config: Optional[Mapping[str, Any]] = ...,
            # TODO: Replace Any with BaseAdapter below
            requests_adapters: Optional[Mapping[str, Any]] = ...,
            raise_on_404: bool = ...,
            user_agent: Optional[str] = ...,
    ) -> None: ...

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

    def get_cookiejar(self) -> requests.cookies.RequestsCookieJar: ...
