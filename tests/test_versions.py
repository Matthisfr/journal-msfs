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
    def test_additional_explicit_store_fields(self):
        self.assertEqual(v.parse_version(page('iniBuilds LOWI Current Version: 1.3.2'),store='inibuilds.com'),'1.3.2')
        self.assertEqual(v.parse_version(page('Contrail LGAV Product Version: 2.4.1'),store='contrail.shop'),'2.4.1')
        self.assertIsNone(v.parse_version(page('Contrail LGAV Updated October 2026'),store='contrail.shop'))
    def test_aerosoft_explicit_edition_only(self):
        html=page('Current version: 3.4 (MSFS 2024) | 2.4 (MSFS 2020)')
        self.assertEqual(v.parse_version(html,store='www.aerosoft.com',edition='MSFS 2024'),'3.4')
        self.assertIsNone(v.parse_version(html,store='www.aerosoft.com',edition='MSFS 2020 / 2024'))
    def test_simmarket(self):
        self.assertEqual(v.parse_version(page('TORONTO CYYZ FLYTAMPA Published by FLYTAMPA Size 430MB Version v1.2 PID 16345'),store='secure.simmarket.com'),'1.2')
        self.assertIsNone(v.parse_version(page('KFSD SIOUX FALLS FSXCENERY Size 43MB Available since 2020-10-11 PID 13893'),store='secure.simmarket.com'))
    def test_glideslope(self):
        self.assertEqual(v.parse_version(page('KIAD Washington Dulles Product version 1.2.7 Download Size 716MB'),store='glideslope.pro'),'1.2.7')
    def test_flightsimto(self):
        self.assertEqual(v.parse_version(page('EuroScene LEPA Downloads 86K Version 2026.09.14'),store='flightsim.to'),'2026.09.14')
    def test_orbx_no_public_version(self):
        self.assertIsNone(v.parse_version(page('Orbx KDEN Denver Version 1.2.3'),store='orbxdirect.com'))
    def test_comparable_trailing_zero(self):
        self.assertEqual(v.compare_versions('2.0.0','2.0','fsxcenery-airport-kmke-milwaukee'),'equal')
        self.assertEqual(v.compare_versions('1.3.0','1.8','tms-airport-egcc-manchester'),'update')
        self.assertEqual(v.compare_versions('1.5.0','1.2','flytampa-airport-cyyz-toronto-pearson'),'source_older')
    def test_comparable_france_vfr(self):
        self.assertEqual(v.compare_versions('1.3.1','1.31','francevfr-airport-lfrn-rennes'),'equal')
        self.assertEqual(v.compare_versions('1.1.0','1.10','francevfr-airport-lfkb-bastia-poretta'),'equal')
        self.assertEqual(v.compare_versions('1.3.1','1.32','francevfr-airport-lfrn-rennes'),'update')
        self.assertEqual(v.compare_versions('1.3.1','1.32','some-other-vendor'),'incomparable')
    def test_compact_zeros(self):
        self.assertEqual(v.compare_versions('1.0.1','1.01','francevfr-airport-lfkj-ajaccio'),'equal')
        self.assertEqual(v.compare_versions('1.0.2','1.01','inibuilds-heliport-58ca-hooper'),'source_older')
        self.assertEqual(v.compare_versions('1.0.0','1.00','doublet-airport-ooms-muscat'),'equal')
    def test_muha_single_major_only(self):
        self.assertEqual(v.compare_versions('2.0.0','2','mexhighflight-airport-muha-jose-marti'),'equal')
        self.assertEqual(v.compare_versions('2.0.0','2','unrelated-airport'),'incomparable')
    def test_euroscene_date_format(self):
        self.assertEqual(v.compare_versions('25.8.5','2026.09.14','euroscene-airport-lepa-palma-de-mallorca'),'update')
        self.assertEqual(v.compare_versions('25.8.5','2025.08.05','euroscene-airport-lepa-palma-de-mallorca'),'equal')
        self.assertEqual(v.compare_versions('25.8.5','2026.09.14','unrelated-airport'),'incomparable')
    def test_semver_safety(self):
        self.assertTrue(v.is_newer('1.0.2','1.0.3'))
        self.assertFalse(v.is_newer('1.0.2','2.0.0'))
        self.assertFalse(v.is_newer('25.8.5','2026.09.14'))
        self.assertFalse(v.is_newer('1.0.2','1.01'))
        self.assertFalse(v.is_newer('1.5.0','1.2'))
        self.assertFalse(v.is_newer('1.5.0','1.2.0'))
if __name__=="__main__":
    unittest.main()
