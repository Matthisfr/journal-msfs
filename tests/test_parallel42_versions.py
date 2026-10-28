import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from parallel42_versions import extract

class Parallel42Tests(unittest.TestCase):
    def test_msfs_2024_and_changelog(self):
        page = """<div>ChasePlane</div><div>Press Release</div><div>Download</div><div>Fri, Aug 14, 2026</div><h2>2026.33.5.14</h2><li>Added Remote UI</li><div>Available here (PC)</div><div>ChasePlane (2020)</div><div>Thu, Jul 17, 2025</div><h2>2026.43.4.2</h2><div>Flow Pro</div><div>Trailer</div><div>Download</div><div>Fri, Aug 14, 2026</div><h2>2026.33.5.13</h2><li>Added support for MSFS 2024 Sim Update 6</li><div>Available here (PC)</div><div>Flow Pro (2020)</div>"""
        chase = extract(page, "ChasePlane")
        flow = extract(page, "Flow Pro")
        self.assertEqual(chase["version"], "2026.33.5.14")
        self.assertEqual(flow["version"], "2026.33.5.13")
        self.assertEqual(flow["date"], "2026-08-14")
        self.assertIn("Sim Update 6", flow["notes"])
    def test_fail_closed(self):
        with self.assertRaises(ValueError):
            extract("<p>Flow Pro (2020)</p><h2>2024.44.4.14</h2>", "Flow Pro")

if __name__ == "__main__":
    unittest.main()
