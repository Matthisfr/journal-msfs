"""Parallel 42 release dashboard parser for MSFS 2024."""
import re
from html.parser import HTMLParser

URL = 'https://parallel42.com/pages/is-it-out'

class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data.strip())

def extract(raw, product):
    parser = Text()
    parser.feed(raw)
    lines = [x for x in parser.parts if x]
    try:
        start = lines.index(product)
    except ValueError:
        raise ValueError('Produit absent du dashboard: ' + product)
    section = lines[start+1:start+65]
    date = next((x for x in section[:8] if re.fullmatch(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),? [A-Z][a-z]{2} \d{2},? 20\d{2}', x)), None)
    version = next((x for x in section[:12] if re.fullmatch(r'v?\d+(?:\.\d+){2,5}', x)), None)
    if not date or not version:
        raise ValueError('Date ou version manquante pour ' + product)
    return {'version':version.lstrip('v'), 'date':date, 'url':URL}
