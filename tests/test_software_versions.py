import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location("software_versions",Path(__file__).resolve().parents[1]/"scripts"/"software_versions.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class SoftwareTests(unittest.TestCase):
    def test_simapppro_changelog(self):
        html="<html><body><h2>SimAppPro</h2><p>1.17.1:</p><p>1.Fix the issue with XPlane.</p><p>1.16.113:</p><p>1.Older fix</p></body></html>"
        with patch.object(v,"get",return_value=html):
            result=v.simapppro_version()
        self.assertEqual(result["version"],"1.17.1")
        self.assertIn("XPlane",result["notes"])
    def test_msfs_official(self):
        html='<html><body><a href="https://www.flightsimulator.com/su71-release/">Release Notes: Sim Update 7.1 [1.9.21.0] Now Available</a></body></html>'
        with patch.object(v,"get",return_value=html):
            result=v.msfs_official()
        self.assertEqual(result["version"],"1.9.21.0")
    def test_fenix_official(self):
        html="<html><body><h1>Fenix A32X Version 3 Released!</h1></body></html>"
        with patch.object(v,"get",return_value=html):
            result=v.fenix_official()
        self.assertEqual(result["version"],"V3 (branche)")
    def test_changelog_summary(self):
        self.assertLessEqual(len(v.short_notes("x"*1300)),900)
if __name__=="__main__":unittest.main()
