import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("import_airports_excel",Path(__file__).resolve().parents[1]/"scripts"/"import_airports_excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def row(section=None,code=None,name=None,folder=None,version=None):
 cells=[None]*13
 if section: cells[3]=section
 if code: cells[6]=code
 if folder: cells[5]=folder
 if name: cells[11]=name
 if version: cells[9]=version
 return tuple(cells)

class FakeSheet:
 def __init__(self,rows): self.rows=rows
 def iter_rows(self,values_only=False): return iter(self.rows)

class AirportImportTests(unittest.TestCase):
 def test_section_sub_heliport_and_duplicates(self):
  sheet=FakeSheet([
   row(section="DECORS (2)"),
   row(code="LFPG",folder="city-paris",name="Paris City",version="1.0"),
   row(section="AEROPORTS (4 / 4)"),
   row(code="LFMN",folder="airport-nice-a",name="Nice",version="1.0"),
   row(code="LFMN",folder="airport-nice-b",name="Nice second edition",version="2.0"),
   row(code="(SUB LFMN)",folder="nice-jetways",name="Jetways",version="1.0"),
   row(code="58CA",folder="inibuilds-heliport-58ca-hooper",name="Hooper Heliport",version="1.0"),
   row(section="VILLES"),
   row(code="KJFK",folder="city-new-york",name="New York City",version="1.0")
  ])
  records=mod.parse_addons_linker(sheet)
  self.assertEqual([x["icao"] for x in records],["LFMN","LFMN","58CA"])
  self.assertEqual(records[-1]["scene_type"],"heliport")
  self.assertEqual(records[0]["scene_type"],"airport")
 def test_missing_section_without_airport_folder_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"Aucune scène aéroport"):
   mod.parse_addons_linker(FakeSheet([row(code="LFPG",folder="city-paris",name="Paris City",version="1.0")]))
 def test_sub_marker(self):
  self.assertTrue(mod.is_sub_scene("(sub LFMN)"))
  self.assertFalse(mod.is_sub_scene("airport-lfmn"))
 def test_merge_retains_metadata(self):
  old=[{"icao":"58CA","name":"Hooper","folder":"hooper-heliport","installed":"1.0","server_version":"1.1","source_url":"https://example.com"}]
  rec=[{"icao":"58CA","name":"Hooper","folder":"hooper-heliport","installed":"1.0","scene_type":"heliport"}]
  merged=mod.merge(rec,old)
  self.assertEqual(merged[0]["source_url"],"https://example.com")
  self.assertEqual(merged[0]["scene_type"],"heliport")

if __name__=="__main__": unittest.main()
