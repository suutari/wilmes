import bs4

from .browser import Browser, _Response
from .form import Form


class StatefulBrowser(Browser):
    def __init__(
            self,
            # session=None,
            # soup_config={'features': 'lxml'},
            # requests_adapters=None,
            # raise_on_404=False,
            # user_agent=None,
    ) -> None: ...

    def absolute_url(self, url: str) -> str: ...

    def open(
            self,
            url: str,
            # *args: ...,
            # **kwargs: ...,
    ) -> _Response: ...

    def open_relative(
            self,
            url: str,
            #*args, **kwargs,
    ) -> _Response: ...

    def select_form(
            self,
            selector: str = ...,
            nr: int = ...,
    ) -> Form: ...

    def __setitem__(self, name: str, value: str) -> None: ...

    def submit_selected(
            self,
            # btnName=None,
            # update_state=True,
            # *args,
            # **kwargs,
    ) -> _Response: ...

    def get_current_page(self) -> bs4.BeautifulSoup: ...
