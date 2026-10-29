"""Tests sans réseau de la veille WINCTRL consacrée à Airbus."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import winctrl_airbus as w


class WinCtrlAirbusTests(unittest.TestCase):
    def test_scope_excludes_boeing_and_generic_articles(self):
        self.assertEqual(w.product_ids("WINWING introduces EFIS control panels for Boeing 737 NG"), [])
        self.assertEqual(w.product_ids("MOZA Airbus captain sticks now available"), [])
        self.assertEqual(w.product_ids("Thrustmaster Airbus EFIS panel"), [])
        self.assertEqual(w.product_ids("WINWING opens orders for Boeing PAP 3 autopilot panel"), [])
        self.assertEqual(w.product_ids("WINCTRL brings force feedback flight controls to FSWeekend"), [])
        self.assertEqual(w.product_ids("WINCTRL OVHD32 SOP full Airbus overhead"), ["ovhd"])
        self.assertEqual(w.product_ids("Winwing Airbus ECAM 32 and AGP 32 Metal panels"), ["ecam","agp"])
        self.assertEqual(w.product_ids("Airbus captain sticks: WINCTRL full-metal left hand"), ["sidestick-metal"])

    def test_date_is_article_date_not_collection_date(self):
        u="https://msfsaddons.com/2026/03/21/winctrls-ovhd32-sop/"
        page='<html><h1>WINCTRL OVHD32 SOP Airbus overhead</h1></html>'
        got=w.from_article(u,page)
        self.assertEqual(got["date"],"2026-03-21")
        self.assertEqual(got["products"],["ovhd"])
        self.assertFalse(w.article_url("https://msfsaddons.com/developer/winctrl/"))

    def test_boeing_does_not_enter_catalog(self):
        listing='<a href="/2026/10/22/airbus-sidestick/"></a><a href="/2026/10/20/boeing-panel/"></a>'
        def fake(url):
            if url==w.INDEX:return listing
            if "sidestick" in url:return "<h1>WINCTRL Airbus captain sticks</h1>"
            return "<h1>WINWING Boeing EFIS 737</h1>"
        items,state=w.records([],fake)
        self.assertEqual(state,"ok")
        self.assertTrue(any(a["products"]==["sidestick-metal"] for a in items))
        self.assertFalse(any("boeing-panel" in a["url"] for a in items))

    def test_bad_source_keeps_verified_baseline(self):
        def offline(_):raise OSError("offline")
        items,state=w.records([],offline)
        self.assertEqual(state,"unavailable")
        self.assertGreaterEqual(len(items),6)
        self.assertEqual(next(a["date"] for a in items if a["products"]==["ovhd"]),"2026-03-21")

    def test_only_verified_host_and_dated_announcement(self):
        self.assertFalse(w.safe_url("https://evil.example/2026/10/22/hardware/"))
        self.assertFalse(w.article_url("http://msfsaddons.com/2026/10/22/foo/"))
        self.assertTrue(w.article_url("https://msfsaddons.com/2026/10/22/foo/"))


if __name__=="__main__":
    unittest.main()
