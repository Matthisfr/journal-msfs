import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("versions",Path(__file__).resolve().parents[1]/"scripts"/"versions.py")
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def page(text):
    return "<html><head><title>Airport</title></head><body><main>"+text+"</main></body></html>"

class VersionTests(unittest.TestCase):
    def test_aerosoft_current(self):
        self.assertEqual(v.parse_version(page('Aerosoft Mega Airport Brussels EBBR Current version: 1.0.5 Version history Version 0.9.1'),store='www.aerosoft.com'),'1.0.5')
    def test_aerosoft_edition_ambiguity(self):
        html=page('Aerosoft Airport Dortmund EDLW Current version: 0.1.0 (MSFS 2024) | 1.0.1 (MSFS 2020)')
        self.assertIsNone(v.parse_version(html,store='www.aerosoft.com',edition='2020+2024'))
        self.assertEqual(v.parse_version(html,store='www.aerosoft.com',edition='2024'),'0.1.0')
    def test_contrail(self):
        self.assertEqual(v.parse_version(page('BGSF Kangerlussuaq Airport Version v1.2.0 Supported Operating System Windows'),store='contrail.shop'),'1.2.0')
    def test_inibuilds(self):
        self.assertEqual(v.parse_version(page('iniBuilds Hooper 58CA Product Size 1.5GB Product Version v1.01 Supported Simulator Version Microsoft Flight Simulator 2020'),store='inibuilds.com'),'1.01')
    def test_simmarket(self):
        self.assertEqual(v.parse_version(page('TORONTO CYYZ FLYTAMPA Published by FLYTAMPA Size 430MB Version v1.2 PID 16345'),store='secure.simmarket.com'),'1.2')
        self.assertIsNone(v.parse_version(page('KFSD SIOUX FALLS FSXCENERY Size 43MB Available since 2020-10-11 PID 13893'),store='secure.simmarket.com'))
    def test_glideslope(self):
        self.assertEqual(v.parse_version(page('KIAD Washington Dulles Product version 1.2.7 Download Size 716MB'),store='glideslope.pro'),'1.2.7')
    def test_flightsimto(self):
        self.assertEqual(v.parse_version(page('EuroScene LEPA Downloads 86K Version 2026.09.14'),store='flightsim.to'),'2026.09.14')
    def test_orbx_no_public_version(self):
        self.assertIsNone(v.parse_version(page('Orbx KDEN Denver Version 1.2.3'),store='orbxdirect.com'))
    def test_semver_safety(self):
        self.assertTrue(v.is_newer('1.0.2','1.0.3'))
        self.assertFalse(v.is_newer('1.0.2','2.0.0'))
        self.assertFalse(v.is_newer('25.8.5','2026.09.14'))
        self.assertFalse(v.is_newer('1.0.2','1.01'))
        self.assertFalse(v.is_newer('1.5.0','1.2'))
        self.assertFalse(v.is_newer('1.5.0','1.2.0'))
if __name__=="__main__":
    unittest.main()
