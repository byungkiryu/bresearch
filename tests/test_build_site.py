import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('build_site', Path(__file__).parents[1] / 'scripts/build_site.py')
build_site = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_site)


class PublicBuildTests(unittest.TestCase):
    def test_hidden_content_and_profile_scalars_are_removed(self):
        source = {'people': [{'id': 'a', 'public': False}, {'id': 'b'}],
                  'events': [{'id': 'e', 'public': False}],
                  'profile': {'email': 'private@example.test', 'scalar_metadata': {'email': {'public': False}},
                              'career': [{'title': 'private job', 'public': False}]},
                  'research': {'topics': [{'title': 'hidden', 'public': False}]}}
        result = build_site.public_site(source)
        self.assertEqual([p['id'] for p in result['people']], ['b'])
        self.assertEqual(result['profile']['email'], '')
        self.assertEqual(result['profile']['career'], [])
        self.assertEqual(result['events'], [])
        self.assertEqual(result['research']['topics'], [])
        self.assertEqual(source['profile']['email'], 'private@example.test')

    def test_images_embed_and_only_linked_attachments_are_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            (root / 'assets/pic.png').write_bytes(b'png fixture')
            (root / 'assets/slides.pdf').write_bytes(b'pdf fixture')
            (root / 'assets/unlinked.pdf').write_bytes(b'unlinked')
            old = build_site.ROOT
            build_site.ROOT = root
            try:
                result, copies = build_site.prepare_assets({'image': 'assets/pic.png', 'links': [{'url': 'assets/slides.pdf'}]})
            finally:
                build_site.ROOT = old
            self.assertTrue(result['image'].startswith('data:image/png;base64,'))
            self.assertEqual(list(copies), ['assets/slides.pdf'])

    def test_asset_cannot_escape_asset_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            old = build_site.ROOT
            build_site.ROOT = Path(directory)
            try:
                with self.assertRaises(ValueError):
                    build_site.prepare_assets({'image': 'assets/../private.png'})
            finally:
                build_site.ROOT = old


if __name__ == '__main__':
    unittest.main()
