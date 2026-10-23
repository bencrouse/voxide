import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine_dependencies import prepare


class EngineDependencyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="voxide-engine-deps-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.cache = self.root / "cache"; self.cache.mkdir()
        self.destination = self.root / "deps"
        self.package = {"name":"test", "revision":"abc", "root":"test-abc", "notice":"LICENSE.txt", "repository":"unused/unused"}

    def archive(self, extra=None):
        path = self.cache / "test-abc.tar.gz"
        with tarfile.open(path, "w:gz") as stream:
            for name, data in (("test-abc/LICENSE.txt", b"test license"), ("test-abc/.hidden", b"hidden content"), ("test-abc/include/test.h", b"header")):
                member = tarfile.TarInfo(name); member.size = len(data); stream.addfile(member, io.BytesIO(data))
            if extra is not None: stream.addfile(extra)
        self.package["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    def test_offline_missing_and_corrupt_archives_are_refused(self):
        with self.assertRaisesRegex(ValueError, "Offline"): prepare(self.package, self.cache, self.destination)
        path = self.archive(); path.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "checksum"): prepare(self.package, self.cache, self.destination)

    def test_hidden_files_and_nested_content_bound_to_archive_each_time(self):
        self.archive()
        first = prepare(self.package, self.cache, self.destination)
        second = prepare(self.package, self.cache, self.destination)
        self.assertEqual(first["tree_sha256"], second["tree_sha256"])
        source = Path(first["source"])
        self.assertEqual((source / ".hidden").read_bytes(), b"hidden content")
        (source / "include/test.h").write_bytes(b"user edit")
        with self.assertRaisesRegex(ValueError, "Edited engine source preserved"):
            prepare(self.package, self.cache, self.destination)
        self.assertEqual((source / "include/test.h").read_bytes(), b"user edit")

    def test_symlinks_traversal_and_extra_files_refused(self):
        for kind in ("symlink", "hardlink", "traversal"):
            member = tarfile.TarInfo("test-abc/link" if kind != "traversal" else "test-abc/../../escape")
            member.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE if kind == "hardlink" else tarfile.DIRTYPE
            member.linkname = "LICENSE.txt"
            self.archive(member)
            with self.subTest(kind=kind), self.assertRaises(ValueError): prepare(self.package, self.cache, self.destination)
        self.archive()
        result = prepare(self.package, self.cache, self.destination)
        (Path(result["source"]) / "extra").write_text("not in verified archive")
        with self.assertRaisesRegex(ValueError, "Edited engine source preserved"): prepare(self.package, self.cache, self.destination)

    def test_concurrent_cold_cache_preparations_share_one_atomic_download(self):
        archive = self.archive()
        payload = archive.read_bytes()
        archive.unlink()  # This test owns the synthetic cache.
        barrier = Barrier(2)
        call_lock = Lock()
        calls = []
        def download(*args,**kwargs):
            with call_lock: calls.append(args[0])
            Event().wait(.1)  # Leave a cold-download overlap for the other worker.
            return io.BytesIO(payload)
        def worker(index):
            barrier.wait(timeout=5)
            return prepare(self.package,self.cache,self.root / ("build-"+str(index)),offline=False)
        with patch("engine_dependencies.urllib.request.urlopen",side_effect=download), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker,(1,2)))
        self.assertEqual(len(calls),1)
        self.assertEqual(results[0]["tree_sha256"],results[1]["tree_sha256"])
        self.assertEqual(archive.read_bytes(),payload)
        self.assertEqual(list(self.cache.glob("engine-download-*")),[])


if __name__ == "__main__": unittest.main()
