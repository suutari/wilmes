import binascii

from bs4.element import Tag

URL_PART = '/cdn-cgi/l/email-protection#'


def unmangle_emails(element: Tag) -> None:
    _replace_email_links(element)
    _replace_email_texts(element)


def _replace_email_links(element: Tag) -> None:
    for a_elem in element.find_all('a'):
        href = a_elem.get('href', '')
        (_before, _sep, after_url_part) = href.partition(URL_PART)
        if after_url_part:
            a_elem['href'] = 'mailto:' + _unmangle(after_url_part)


def _replace_email_texts(element: Tag) -> None:
    for elem in element.find_all(attrs={'class': '__cf_email__'}):
        hex_string = elem.get('data-cfemail')
        if hex_string:
            email = _unmangle(hex_string)
            elem.replace_with(email)


def _unmangle(hex_string: str) -> str:
    values = binascii.unhexlify(hex_string)
    first_val = values[0]
    return ''.join(chr(x ^ first_val) for x in values[1:])
