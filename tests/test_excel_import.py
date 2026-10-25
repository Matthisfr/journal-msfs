"""Offline regression tests for Excel import, including duplicates and version resets."""
import importlib.util, pathlib, tempfile, unittest
from openpyxl import Workbook
SCRIPT=pathlib.Path(__file__).resolve().parents[1]/"scripts"/"import_airports_excel.py"
spec=importlib.util.spec_from_file_location("excel_import",SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class ExcelImportTests(unittest.TestCase):
 def test_import_merge_and_corrections(self):
  wb=Workbook()
  ws=wb.active
  ws.append(["Code ICAO","Nom","Dossier","Éditeur","Version installée","Région"])
  ws.append(["BCGB","Gibraltar","gibraltar-a","Studio A","1.2.0","EUROPE"])
  ws.append(["BCGB","Gibraltar second scenery","gibraltar-b","Studio B","2.0.0","EUROPE"])
  ws.append(["KABK","Albuquerque","albuquerque","Studio C","1.0.0","USA"])
  ws.append(["KLVB","Fictional","venice-beach","Studio D","1.0","USA"])
  with tempfile.TemporaryDirectory() as directory:
   path=pathlib.Path(directory)/"test.xlsx"
   wb.save(path)
   rows=module.parse(path)
  self.assertEqual(len(rows),3)
  self.assertEqual([r["icao"] for r in rows],["LXGB","LXGB","KABQ"])
  old=[dict(rows[0],server_version="1.2.0",version_check_state="verified",version_checked_at="2026-10-25")]
  merged=module.merge(rows,old)
  self.assertEqual(len(merged),3)
  self.assertEqual(merged[0]["server_version"],"1.2.0")
  rows[0]["installed"]="1.3.0"
  updated=module.merge(rows,old)
  self.assertNotIn("server_version",updated[0])
 def test_reject_duplicate_folder(self):
  row={"icao":"LFPG","original":"LFPG","name":"Paris","folder":"same","installed":"1","publisher":"A","region":"EUROPE"}
  with self.assertRaises(ValueError): module.merge([row,row],[])
if __name__=="__main__":unittest.main()
