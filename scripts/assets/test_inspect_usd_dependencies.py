import tempfile
import unittest
from pathlib import Path
from pxr import Sdf, Usd
from inspect_usd_dependencies import inspect


class DependencyTests(unittest.TestCase):
    def test_resolved_and_missing_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = Usd.Stage.CreateNew(str(root / 'child.usda'))
            child.DefinePrim('/Object', 'Xform')
            child.SetDefaultPrim(child.GetPrimAtPath('/Object'))
            child.GetRootLayer().Save()
            stage = Usd.Stage.CreateNew(str(root / 'scene.usda'))
            obj = stage.DefinePrim('/Object', 'Xform')
            obj.GetReferences().AddReference('child.usda')
            obj.CreateAttribute('texture', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('missing.png'))
            stage.GetRootLayer().Save()
            bad = inspect(root / 'scene.usda')
            self.assertFalse(bad['usd_dependency_resolution_passed'])
            self.assertTrue(any('missing.png' in path for path in bad['unresolved']))
            self.assertEqual(len(bad['layers']), 2)
            (root / 'missing.png').write_bytes(b'fixture')
            good = inspect(root / 'scene.usda')
            self.assertTrue(good['usd_dependency_resolution_passed'])
            self.assertTrue(any('missing.png' in path for path in good['assets']))


if __name__ == '__main__':
    unittest.main()
