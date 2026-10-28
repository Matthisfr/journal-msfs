import datetime as dt
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from editorial_news import SOURCES,collect_source,normalize_article

NOW=dt.datetime(2026,10,28,tzinfo=dt.timezone.utc)
SOURCE=SOURCES[0]
URL="https://fselite.net/2026/10/27/fsdreamteam-gsx-pro-update/"
ARTICLE='''<script type="application/ld+json">{"@type":"NewsArticle","headline":"FSDreamTeam GSX Pro update released","datePublished":"2026-10-27T10:00:00Z","url":"https://fselite.net/2026/10/27/fsdreamteam-gsx-pro-update/","description":"GSX improvements"}</script>'''
class EditorialNewsTests(unittest.TestCase):
    def test_article(self):
        article={"@type":"NewsArticle","headline":"FSDreamTeam GSX Pro update released","datePublished":"2026-10-27T10:00:00Z","url":URL}
        self.assertEqual(normalize_article(article,SOURCE,NOW)["category"],"GSX Pro")
    def test_unrelated_article_excluded(self):
        article={"headline":"Boeing released a new aircraft","datePublished":"2026-10-27T10:00:00Z","url":URL}
        self.assertIsNone(normalize_article(article,SOURCE,NOW))
    def test_fetch_listing_and_article(self):
        def fetcher(url,host):
            if url==SOURCE["url"]:return '<a href="'+URL+'">GSX</a>'
            return ARTICLE
        news,state=collect_source(SOURCE,[],fetcher,NOW)
        self.assertEqual(state,"ok")
        self.assertEqual(len(news),1)
        self.assertEqual(news[0]["date"],"2026-10-27")
    def test_missing_article_does_not_fake_news(self):
        news,state=collect_source(SOURCE,[],lambda url,host:"<html></html>",NOW)
        self.assertEqual((news,state),([],"no_dated_articles"))
if __name__=="__main__":unittest.main()
