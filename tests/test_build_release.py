"""Run with python -m unittest discover -s tests -p test_build_release.py."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_release', ROOT / 'scripts' / 'build_release.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    def test_installable_package_contains_only_runtime_files_and_license(self):
        with tempfile.TemporaryDirectory(prefix='facial_shapekeys_build_test_') as directory:
            archive_path = Path(directory) / 'addon.zip'
            builder.build_archive(archive_path)
            with ZipFile(archive_path) as archive:
                names = archive.namelist()
                for filename in builder.ROOT_FILES:
                    self.assertIn(builder.PACKAGE_NAME + '/' + filename, names)
                self.assertIn(builder.PACKAGE_NAME + '/operators/shape_key_sort.py', names)
                for name in names:
                    relative = Path(name).relative_to(builder.PACKAGE_NAME)
                    self.assertTrue(str(relative) in builder.ROOT_FILES
                                    or (relative.parts[0] in builder.MODULE_DIRECTORIES
                                        and len(relative.parts) == 2 and relative.suffix == '.py'))
                self.assertIsNone(archive.testzip())

    def test_zip_is_identical_across_builds_and_line_ending_conventions(self):
        with tempfile.TemporaryDirectory(prefix='facial_shapekeys_build_test_') as directory:
            temporary = Path(directory)
            first = temporary / 'first.zip'
            second = temporary / 'second.zip'
            builder.build_archive(first)
            builder.build_archive(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            # Copy only the runtime inputs to simulate a Linux checkout in a different directory.
            root = temporary / 'different-checkout-name'
            with ZipFile(first) as archive:
                for name in archive.namelist():
                    relative = Path(name).relative_to(builder.PACKAGE_NAME)
                    destination = root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(name))
            builder.build_archive(second, root=root)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_tag_must_match_version_before_an_existing_archive_is_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='facial_shapekeys_build_test_') as directory:
            archive_path = Path(directory) / 'addon.zip'
            archive_path.write_bytes(b'keep existing archive')
            with self.assertRaisesRegex(ValueError, 'does not match add-on version'):
                builder.build_archive(archive_path, tag='v999.0.0')
            self.assertEqual(archive_path.read_bytes(), b'keep existing archive')


if __name__ == '__main__':
    unittest.main()
