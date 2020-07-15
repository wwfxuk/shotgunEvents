import html.parser

parser = html.parser.HTMLParser()


def parseHtml(text):
    if not text:
        None
    else:
        try:
            return parser.unescape(text)
        except UnicodeDecodeError:
            return "Failed to parse text: {0}".format(text)
