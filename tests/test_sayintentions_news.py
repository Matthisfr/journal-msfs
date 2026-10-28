import datetime as dt
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from sayintentions_news import parse_feed,parse_html_articles,normalize

NOW=dt.datetime(2026,10,28,tzinfo=dt.timezone.utc)
class NewsExtractorTests(unittest.TestCase):
    def test_rss_article_and_duplicate(self):
        xml="""<rss><channel><item><title>Community Crew is now live</title><link>https://www.sayintentions.ai/blog/community-crew</link><pubDate>Mon, 26 Oct 2026 19:00:00 GMT</pubDate><description>New voices</description></item></channel></rss>"""
        records=parse_feed(xml)
        self.assertEqual(len(normalize(records,[],NOW)),1)
        self.assertFalse(normalize(records,[{"url":"https://www.sayintentions.ai/blog/community-crew"}],NOW)[0]["new"])
    def test_json_ld(self):
        page="""<script type="application/ld+json">{"@graph":[{"@type":"BlogPosting","headline":"Progressive Taxi available to everyone","url":"https://www.sayintentions.ai/blog/progressive-taxi","datePublished":"2026-10-23T16:00:00Z"}]}</script>"""
        records,_=parse_html_articles(page)
        self.assertEqual(normalize(records,[],NOW)[0]["date"],"2026-10-23")
    def test_undated_and_foreign_rejected(self):
        records=[{"title":"Fake headline","url":"https://evil.example/blog/foo","published":"2026-10-26"},
                 {"title":"Undated headline","url":"https://www.sayintentions.ai/blog/foo"}]
        self.assertEqual(normalize(records,[],NOW),[])
    def test_discover_html_links(self):
        _,parser=parse_html_articles('<a href="/blog/some-article">Article</a>')
        self.assertEqual(parser.articles,["https://www.sayintentions.ai/blog/some-article"])
if __name__=="__main__":unittest.main()
