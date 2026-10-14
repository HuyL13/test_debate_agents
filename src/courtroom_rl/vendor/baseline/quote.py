def _normalize_quote_text(text):
    for dash in ('\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2212'):
        text = text.replace(dash, '-')
    for quote in ('\u2018', '\u2019', '\u201a', '\u201b'):
        text = text.replace(quote, "'")
    for quote in ('\u201c', '\u201d', '\u201e', '\u201f'):
        text = text.replace(quote, '"')
    return ' '.join(text.split())
