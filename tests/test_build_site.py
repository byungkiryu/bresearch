import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('build_site', Path(__file__).parents[1] / 'scripts/build_site.py')
build_site = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_site)


class PublicBuildTests(unittest.TestCase):
    def test_standalone_event_pages_keep_urls_without_publishing_source_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'src/events/2026-11-20'
            source.mkdir(parents=True)
            html = '<!doctype html><title>Workshop</title><p>α-MgAgSb · Sb₂Te₃</p>'
            (source / 'index.html').write_text(html, encoding='utf-8')
            (source / 'draft-notes.txt').write_text('private editorial note')
            out = root / 'dist'
            stale = out / 'events/old-event'
            stale.mkdir(parents=True)
            (stale / 'index.html').write_text('removed event')
            old = build_site.ROOT
            build_site.ROOT = root
            try:
                pages = build_site.copy_event_pages(out)
            finally:
                build_site.ROOT = old
            self.assertEqual(pages, ['events/2026-11-20/index.html'])
            self.assertEqual((out / pages[0]).read_text(encoding='utf-8'), html)
            self.assertEqual([p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()], pages)

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

    def test_research_projects_and_facilities_filter_hidden_and_keep_order(self):
        source = {'research': {
            name: [{'id': f'{name}-later', 'order': 3},
                   {'id': f'{name}-hidden', 'order': 1, 'public': False},
                   {'id': f'{name}-first', 'order': 2, 'public': True}]
            for name in ('projects', 'facilities')
        }}
        result = build_site.public_site(source)
        for name in ('projects', 'facilities'):
            self.assertEqual([row['id'] for row in result['research'][name]],
                             [f'{name}-first', f'{name}-later'])
            self.assertEqual(len(source['research'][name]), 3)

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
