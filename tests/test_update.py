import datetime as dt
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('update',Path(__file__).resolve().parents[1]/'scripts'/'update.py')
u=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(u)

class UpdateTests(unittest.TestCase):
    def test_severity_order(self):
        clear=u.severity({'rawOb':'LFMN 250600Z 22010KT CAVOK','visib':10})
        fog=u.severity({'rawOb':'LFPO 250600Z 08005KT 0300 FG OVC001','wxString':'FG','visib':0.3,'ceil':100})
        storm=u.severity({'rawOb':'LFPG 250600Z 27035G43KT 1500 +TSRA BKN006','wxString':'+TSRA','visib':1,'ceil':600,'wgst':43})
        self.assertGreater(storm[0],fog[0])
        self.assertGreater(fog[0],clear[0])
        self.assertEqual(storm[2],'⛈️')

    def test_metar_top10_and_taf(self):
        when=(u.NOW-dt.timedelta(minutes=20)).isoformat()
        metars=[
          {'icaoId':'LFMN','obsTime':when,'rawOb':'LFMN 250600Z 20015KT CAVOK','visib':10},
          {'icaoId':'LFPG','obsTime':when,'rawOb':'LFPG 250600Z 28035G43KT 1500 +TSRA BKN006','wxString':'+TSRA','visib':1,'ceil':600,'wgst':43}]
        def fake_get(url,**kw):
            if 'metar?' in url: return __import__('json').dumps(metars).encode()
            if 'taf?' in url: return b'[{"icaoId":"LFPG","rawTAF":"TAF LFPG 250500Z 2506/2612 28020KT"}]'
            raise AssertionError(url)
        with patch.object(u,'get',side_effect=fake_get),patch.object(u.time,'sleep'):
            top,coverage,state,taf,errors=u.collect_weather([
              {'icao':'LFPG','name':'Paris'},{'icao':'LFMN','name':'Nice'},
              {'icao':'KLVB','name':'Fictif'},{'icao':'58CA','name':'Local'}])
        self.assertEqual(coverage['eligible'],2)
        self.assertEqual(coverage['fresh'],2)
        self.assertEqual(top[0]['icao'],'LFPG')
        self.assertTrue(top[0]['taf_raw'].startswith('TAF LFPG'))
        self.assertEqual(state,'ok')

    def test_official_rss(self):
        recent=u.NOW-dt.timedelta(hours=4)
        pub=__import__('email.utils',fromlist=['format_datetime']).format_datetime(recent)
        xml=f'<rss><channel><item><title>Sim Update 7.2</title><link>https://forums.flightsimulator.com/t/abc/123</link><pubDate>{pub}</pubDate><description>Official release</description></item></channel></rss>'
        with patch.object(u,'get',return_value=xml.encode()):
            result=u.collect_news([])
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]['new'])

if __name__=='__main__': unittest.main()
