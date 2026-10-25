import tempfile,unittest,zipfile,stat
from pathlib import Path
from unpack_verified import extract
class ExtractTests(unittest.TestCase):
 def test_relative_asset_link_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);z=p/'a.zip'
   with zipfile.ZipFile(z,'w') as f:
    f.writestr('Materials/a.mdl','material');link=zipfile.ZipInfo('scenes/Materials');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16;f.writestr(link,'../Materials')
   r=extract(z,p/'out');self.assertEqual(r['symlinks'],1);self.assertEqual((p/'out/scenes/Materials/a.mdl').read_text(),'material')
 def test_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);z=p/'a.zip'
   with zipfile.ZipFile(z,'w') as f:f.writestr('../escape','bad')
   with self.assertRaises(ValueError):extract(z,p/'out')
   self.assertFalse((p/'escape').exists())
if __name__=='__main__':unittest.main()
