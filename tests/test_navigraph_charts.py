import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from software_versions import parse_navigraph_charts_changelog

URL='https://navigraph.com/products/charts/changelog'

class NavigraphChartsTests(unittest.TestCase):
    def test_releases_and_notes(self):
        page='# 8.44.0\nOld changes\n# 8.45.0\nNew VFR charts\n# 8.45.1\nFixed map loading\n'
        result=parse_navigraph_charts_changelog(page,URL)
        self.assertEqual(result['version'],'8.45.1')
        self.assertIn('Fixed map loading',result['notes'])
    def test_reject_unlabelled_assets(self):
        with self.assertRaises(ValueError):
            parse_navigraph_charts_changelog("<script src='bundle-8.99.0.js'></script>",URL)
    def test_explicit_charts(self):
        self.assertEqual(parse_navigraph_charts_changelog('Navigraph Charts Version 8.45.1\nRelease fixes',URL)['version'],'8.45.1')

if __name__=='__main__': unittest.main()
