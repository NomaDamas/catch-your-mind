"""Owned metadata bootstrap probes never read FIFO or follow package symlinks."""
import csv
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.recorded_source import digest
from benchmarks.recording_dependencies import distribution_descriptor,verify_dependencies,VerifiedDependencyInventory


class Dependencies(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='.')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.site=self.root/'site';self.site.mkdir();self.meta=self.site/'example-1.0.dist-info';self.meta.mkdir()
        (self.meta/'METADATA').write_bytes(b'Name: example\nVersion: 1.0\n\nfixture\n')
        (self.site/'example.py').write_bytes(b'value = 1\n')
        self.paths=['example.py','example-1.0.dist-info/METADATA','example-1.0.dist-info/RECORD']
        self.write_record()
    def write_record(self,extra=()):
        out=StringIO();writer=csv.writer(out,lineterminator='\n')
        for name in self.paths+list(extra):writer.writerow([name,'',''])
        (self.meta/'RECORD').write_text(out.getvalue())
    def descriptor(self):return distribution_descriptor('example',allowed_roots=(self.root,),metadata_roots=(self.site,))
    def test_actual_owned_bytes_private_receipt_and_mutation_rejection(self):
        descriptor=self.descriptor();entry=dict(distribution='example',version='1.0',installation_sha256=digest(descriptor))
        verified=verify_dependencies([entry],allowed_roots=(self.root,),metadata_roots=(self.site,))
        self.assertEqual(verified.sha256,digest([entry]));self.assertEqual(verified.require('example','1.0'),entry)
        self.assertEqual([r['path'] for r in descriptor['files']],sorted(self.paths))
        with self.assertRaises(TypeError):VerifiedDependencyInventory([entry])
        (self.site/'example.py').write_bytes(b'value = 2\n')
        with self.assertRaises(ValueError):verify_dependencies([entry],allowed_roots=(self.root,),metadata_roots=(self.site,))
    def test_metadata_and_record_fifo_refuse_without_blocking_or_importlib_reads(self):
        for filename in ('METADATA','RECORD'):
            path=self.meta/filename;original=path.read_bytes();path.rename(self.meta/(filename+'.saved'));os.mkfifo(path)
            try:
                with patch('importlib.metadata.distribution',side_effect=AssertionError('unowned bootstrap')):
                    with self.assertRaises(ValueError):self.descriptor()
            finally:
                path.unlink();(self.meta/(filename+'.saved')).rename(path)
    def test_symlink_outside_alias_metadata_and_joint_admission_refuse(self):
        file=self.site/'example.py';file.rename(self.site/'original.py');file.symlink_to(self.site/'original.py')
        with self.assertRaises(OSError):self.descriptor()
        file.unlink();(self.site/'original.py').rename(file)
        self.write_record(('example.py',))
        self.assertEqual(len(self.descriptor()['files']),3)
        self.write_record(('./example.py',))
        with self.assertRaisesRegex(ValueError,'aliases'):self.descriptor()
        self.write_record(('../../not-owned',))
        with self.assertRaisesRegex(ValueError,'outside'):self.descriptor()
    def test_bootstrap_byte_and_line_limits_precede_parsing(self):
        (self.meta/'METADATA').write_bytes(b'x'*(1024**2+1))
        with self.assertRaises(ValueError):self.descriptor()
        (self.meta/'METADATA').write_bytes(b'Name: example\nVersion: 1.0\n'+b'\r'*9000)
        with self.assertRaisesRegex(ValueError,'line count'):self.descriptor()
