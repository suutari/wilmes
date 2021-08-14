import bs4

from wilmes._email_unmangling import unmangle_emails


def test_unmangling() -> None:
    hexstring = '88dcedfbfca6cde5e9e1e4c8edf0e9e5f8e4eda6ebe7e5'
    doc = bs4.BeautifulSoup((
        '<html>'
        '<body>'
        '<a href="/cdn-cgi/l/email-protection#{hexstring}">protected1</a>'
        '<div>'
        '<a href="/cdn-cgi/l/email-protection"'
        '   class="__cf_email__" data-cfemail="{hexstring}">protected2</a>'
        '</div>'
        '<a href="/some-uri">normal link</a>'
        '<a href="/cdn-cgi/l/email-protection#{hexstring}">protected3</a>'
        '</body>'
        '</html>').format(**locals()), features='lxml')

    unmangle_emails(doc)

    email = 'Test.Email@example.com'
    assert str(doc) == (
        '<html>'
        '<body>'
        '<a href="mailto:{email}">protected1</a>'
        '<div>{email}</div>'
        '<a href="/some-uri">normal link</a>'
        '<a href="mailto:{email}">protected3</a>'
        '</body>'
        '</html>'
    ).format(**locals())


if __name__ == '__main__':
    test_unmangling()
