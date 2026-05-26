#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "resolve_meta.py"))


def run(*args, env=None):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True, env=env,
    )


class Fixture:
    def __init__(self, tmp):
        self.tmp = tmp

    def meta(self, pkg_vars=None, build_deps=None, runtime_deps=None):
        data = {
            "package": {"name": "test", "variables": pkg_vars or {}},
            "dependencies": {"direct": {
                "build": build_deps or [],
                "runtime": runtime_deps or [],
            }},
        }
        path = os.path.join(self.tmp, ".meta.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def dep(self, name, variables):
        return {"name": name, "variables": variables}

    def file(self, content, name="input.txt"):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as f:
            f.write(content)
        return path


class TestBasicResolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f = Fixture(self.tmp)

    def test_package_var(self):
        meta = self.f.meta(pkg_vars={"greeting": "hello"})
        inp = self.f.file("say %(greeting)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "say hello")

    def test_build_dep_var(self):
        meta = self.f.meta(build_deps=[self.f.dep("libfoo", {"prefix": "/usr/local"})])
        inp = self.f.file("install to %(prefix)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "install to /usr/local")

    def test_runtime_dep_var(self):
        meta = self.f.meta(runtime_deps=[self.f.dep("libbar", {"libdir": "/lib64"})])
        inp = self.f.file("libs at %(libdir)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "libs at /lib64")

    def test_no_placeholders(self):
        meta = self.f.meta(pkg_vars={"x": "y"})
        inp = self.f.file("no placeholders here")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "no placeholders here")

    def test_whitespace_stripped_from_var_names(self):
        meta = self.f.meta(pkg_vars={" spaced ": "value"})
        inp = self.f.file("%(spaced)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "value")

    def test_integer_variable_value(self):
        meta = self.f.meta(pkg_vars={"count": 42})
        inp = self.f.file("count=%(count)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "count=42")

    def test_bare_percent_chars_preserved(self):
        # Files with bare % (e.g. %", %d, 100%) must not crash
        meta = self.f.meta(pkg_vars={"version": "42"})
        inp = self.f.file('cflags="-O2" # 100% done, version %(version)s, fmt="%d"')
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertIn('100%', r.stdout)
        self.assertIn('"%d"', r.stdout)
        self.assertIn('version 42', r.stdout)

    def test_existing_fixtures(self):
        root = os.path.dirname(SCRIPT)
        r = run(
            os.path.join(root, "test.xml"),
            "--meta", os.path.join(root, "test.json"),
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("johnny", r.stdout)
        self.assertIn("gosling", r.stdout)


class TestRecursiveResolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f = Fixture(self.tmp)

    def test_var_references_var(self):
        # %(full)s = "%(first)s %(last)s" should resolve in two passes
        meta = self.f.meta(pkg_vars={"first": "John", "last": "Doe", "full": "%(first)s %(last)s"})
        inp = self.f.file("Hello %(full)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "Hello John Doe")

    def test_circular_reference_errors(self):
        # %(a)s = "%(b)s", %(b)s = "%(a)s" — must error, not silently return garbage
        meta = self.f.meta(pkg_vars={"a": "%(b)s", "b": "%(a)s"})
        inp = self.f.file("%(a)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0, "circular reference should be a fatal error")
        self.assertIn("ERROR", r.stderr)

    def test_var_value_introduces_unknown_placeholder(self):
        # %(a)s = "%(ghost)s" but ghost is never defined — must give clear error
        meta = self.f.meta(pkg_vars={"a": "%(ghost)s"})
        inp = self.f.file("%(a)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0, "undefined placeholder introduced by substitution should error")
        self.assertIn("ERROR", r.stderr)


class TestConflictDetection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f = Fixture(self.tmp)

    def test_dep_dep_conflict(self):
        meta = self.f.meta(build_deps=[
            self.f.dep("depA", {"shared": "from_A"}),
            self.f.dep("depB", {"shared": "from_B"}),
        ])
        inp = self.f.file("%(shared)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("multiple deps", r.stderr)
        self.assertIn("shared", r.stderr)

    def test_dep_dep_conflict_three_way(self):
        meta = self.f.meta(build_deps=[
            self.f.dep("A", {"x": "1"}),
            self.f.dep("B", {"x": "2"}),
            self.f.dep("C", {"x": "3"}),
        ])
        inp = self.f.file("%(x)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("A", r.stderr)
        self.assertIn("B", r.stderr)
        self.assertIn("C", r.stderr)

    def test_dep_pkg_conflict(self):
        meta = self.f.meta(
            pkg_vars={"foo": "pkg_val"},
            build_deps=[self.f.dep("dep1", {"foo": "dep_val"})],
        )
        inp = self.f.file("%(foo)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("conflicts with package variable", r.stderr)

    def test_build_and_runtime_conflict(self):
        # Same var in a build dep and a runtime dep should also conflict
        meta = self.f.meta(
            build_deps=[self.f.dep("bdep", {"shared": "build_val"})],
            runtime_deps=[self.f.dep("rdep", {"shared": "runtime_val"})],
        )
        inp = self.f.file("%(shared)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("multiple deps", r.stderr)


class TestDefaultValues(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f = Fixture(self.tmp)

    def test_default_used_when_key_absent(self):
        meta = self.f.meta()
        inp = self.f.file("%(enable_vecgeom:-0)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "0")

    def test_defined_value_overrides_default(self):
        meta = self.f.meta(pkg_vars={"enable_vecgeom": "1"})
        inp = self.f.file("%(enable_vecgeom:-0)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "1")

    def test_empty_string_default(self):
        meta = self.f.meta()
        inp = self.f.file("x=%(missing:-  )s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "x=")

    def test_default_with_other_placeholders(self):
        meta = self.f.meta(pkg_vars={"name": "alice"})
        inp = self.f.file("%(name)s %(role:-user)s")
        r = run(inp, "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "alice user")

    def test_default_visible_in_list_vars(self):
        meta = self.f.meta()
        # --list-vars only shows meta vars, not inline defaults (they aren't in the meta)
        r = run("--list-vars", "--meta", meta)
        self.assertEqual(r.returncode, 0)


class TestMissingVars(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f = Fixture(self.tmp)

    def test_placeholder_not_in_meta(self):
        meta = self.f.meta(pkg_vars={"defined": "yes"})
        inp = self.f.file("%(defined)s %(undefined)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("undefined", r.stderr)

    def test_multiple_missing_placeholders(self):
        meta = self.f.meta()
        inp = self.f.file("%(a)s %(b)s %(c)s")
        r = run(inp, "--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        for key in ("a", "b", "c"):
            self.assertIn(key, r.stderr)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f = Fixture(self.tmp)

    def test_list_vars(self):
        meta = self.f.meta(
            pkg_vars={"pkg_key": "pkg_val"},
            build_deps=[self.f.dep("dep1", {"dep_key": "dep_val"})],
        )
        r = run("--list-vars", "--meta", meta)
        self.assertEqual(r.returncode, 0)
        self.assertIn("pkg_key", r.stdout)
        self.assertIn("dep_key", r.stdout)

    def test_missing_file_arg(self):
        meta = self.f.meta()
        r = run("--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ERROR", r.stderr)

    def test_nonexistent_file(self):
        meta = self.f.meta()
        r = run("/nonexistent/path/file.txt", "--meta", meta)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ERROR", r.stderr)

    def test_nonexistent_meta(self):
        inp = self.f.file("hello")
        r = run(inp, "--meta", "/nonexistent/.meta.json")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ERROR", r.stderr)

    def test_missing_installroot(self):
        inp = self.f.file("hello")
        env = {k: v for k, v in os.environ.items() if k != "INSTALLROOT"}
        r = run(inp, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("INSTALLROOT", r.stderr)

    def test_installroot_env_var(self):
        meta = self.f.meta(pkg_vars={"x": "y"})
        inp = self.f.file("%(x)s")
        env = {**os.environ, "INSTALLROOT": self.tmp}
        r = run(inp, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "y")


if __name__ == "__main__":
    unittest.main(verbosity=2)
