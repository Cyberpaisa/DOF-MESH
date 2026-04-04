"""
tests/test_session_resume.py
─────────────────────────────
Tests para core/session_resume.py.

Suite:
    TestDaemonSession       — dataclass DaemonSession (métodos, serialización)
    TestSessionStoreSave    — save() en distintos escenarios
    TestSessionStoreLoad    — load() con archivo ausente / corrupto / expirado / válido
    TestSessionStoreClear   — clear() y reset()
    TestSessionStoreAtomic  — escritura atómica (crash-safety)
    TestSessionStorePath    — property session_path
    TestSessionStoreRepr    — __repr__
"""

import json
import os
import sys
import tempfile
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.session_resume import (
    DaemonSession,
    MAX_SESSION_AGE_SECONDS,
    SessionStore,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_session(**overrides) -> DaemonSession:
    """Crea una DaemonSession con valores por defecto sobrescribibles."""
    defaults = dict(
        session_id="test-uuid-1234",
        daemon_type="default",
        cycle_count=5,
        total_improvements=2,
        started_at=time.time() - 100,
        last_updated_at=time.time() - 10,
    )
    defaults.update(overrides)
    return DaemonSession(**defaults)


def _make_store(daemon_type="default", **kwargs) -> "tuple[SessionStore, str]":
    """
    Crea un SessionStore apuntando a un directorio temporal.
    Retorna (store, tmpdir) — el caller es responsable de limpiar tmpdir.
    """
    tmpdir = tempfile.mkdtemp()
    store = SessionStore(daemon_type=daemon_type, base_dir=tmpdir, **kwargs)
    return store, tmpdir


# ─────────────────────────────────────────────────────────────────────────────
# TestDaemonSession
# ─────────────────────────────────────────────────────────────────────────────

class TestDaemonSession(unittest.TestCase):
    """Comportamiento de la dataclass DaemonSession."""

    def setUp(self):
        self.now = time.time()
        self.session = _make_session(
            started_at=self.now - 200,
            last_updated_at=self.now - 50,
        )

    # ── age_seconds ──────────────────────────────────────────────────────────

    def test_age_seconds_reflects_elapsed_time(self):
        age = self.session.age_seconds()
        # Debe ser ~50s (50 segundos desde last_updated_at)
        self.assertGreater(age, 40)
        self.assertLess(age, 70)

    def test_age_seconds_increases_over_time(self):
        age1 = self.session.age_seconds()
        time.sleep(0.05)
        age2 = self.session.age_seconds()
        self.assertGreater(age2, age1)

    # ── is_expired ───────────────────────────────────────────────────────────

    def test_is_expired_returns_false_for_fresh_session(self):
        session = _make_session(last_updated_at=time.time() - 10)
        self.assertFalse(session.is_expired(max_age=86400))

    def test_is_expired_returns_true_for_old_session(self):
        session = _make_session(last_updated_at=time.time() - 100)
        self.assertTrue(session.is_expired(max_age=50))

    def test_is_expired_uses_default_max_age(self):
        """Session de 23h NO está expirada con el default de 24h."""
        session = _make_session(last_updated_at=time.time() - 82800)  # 23h
        self.assertFalse(session.is_expired())

    def test_is_expired_at_exactly_boundary(self):
        """Session de exactamente 24h+1s SÍ está expirada."""
        session = _make_session(last_updated_at=time.time() - (MAX_SESSION_AGE_SECONDS + 1))
        self.assertTrue(session.is_expired())

    # ── to_dict / from_dict ──────────────────────────────────────────────────

    def test_to_dict_returns_all_fields(self):
        d = self.session.to_dict()
        for field in ("session_id", "daemon_type", "cycle_count",
                      "total_improvements", "started_at", "last_updated_at"):
            self.assertIn(field, d)

    def test_to_dict_values_match_session(self):
        d = self.session.to_dict()
        self.assertEqual(d["cycle_count"], self.session.cycle_count)
        self.assertEqual(d["daemon_type"], self.session.daemon_type)

    def test_from_dict_roundtrip(self):
        original = self.session
        restored = DaemonSession.from_dict(original.to_dict())
        self.assertEqual(restored.session_id, original.session_id)
        self.assertEqual(restored.daemon_type, original.daemon_type)
        self.assertEqual(restored.cycle_count, original.cycle_count)
        self.assertEqual(restored.total_improvements, original.total_improvements)
        self.assertAlmostEqual(restored.started_at, original.started_at, places=3)
        self.assertAlmostEqual(restored.last_updated_at, original.last_updated_at, places=3)

    def test_from_dict_raises_on_missing_field(self):
        d = self.session.to_dict()
        del d["cycle_count"]
        with self.assertRaises(KeyError):
            DaemonSession.from_dict(d)

    def test_from_dict_coerces_numeric_strings(self):
        """cycle_count como string numérico debe funcionar vía int()."""
        d = self.session.to_dict()
        d["cycle_count"] = "7"
        d["total_improvements"] = "3"
        session = DaemonSession.from_dict(d)
        self.assertEqual(session.cycle_count, 7)
        self.assertEqual(session.total_improvements, 3)

    # ── repr ─────────────────────────────────────────────────────────────────

    def test_repr_includes_key_fields(self):
        r = repr(self.session)
        self.assertIn("default", r)
        self.assertIn("5", r)  # cycle_count


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionStoreSave
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionStoreSave(unittest.TestCase):
    """save() escribe a disco y mantiene estado en memoria."""

    def test_save_creates_session_file(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=3, total_improvements=1)
        self.assertTrue(os.path.exists(store.session_path))

    def test_save_writes_valid_json(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=3, total_improvements=1)
        with open(store.session_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["cycle_count"], 3)
        self.assertEqual(data["total_improvements"], 1)

    def test_save_creates_session_id_on_first_call(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        self.assertIsNotNone(store.current_session)
        self.assertIsNotNone(store.current_session.session_id)
        self.assertGreater(len(store.current_session.session_id), 0)

    def test_save_preserves_session_id_across_calls(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        sid1 = store.current_session.session_id
        store.save(cycle_count=2, total_improvements=1)
        sid2 = store.current_session.session_id
        self.assertEqual(sid1, sid2, "session_id no debe cambiar en la misma sesión")

    def test_save_updates_cycle_count(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        store.save(cycle_count=5, total_improvements=2)
        with open(store.session_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["cycle_count"], 5)

    def test_save_updates_last_updated_at(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        t1 = store.current_session.last_updated_at
        time.sleep(0.05)
        store.save(cycle_count=2, total_improvements=0)
        t2 = store.current_session.last_updated_at
        self.assertGreater(t2, t1)

    def test_save_sets_started_at_only_once(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        t_start = store.current_session.started_at
        time.sleep(0.05)
        store.save(cycle_count=2, total_improvements=0)
        self.assertAlmostEqual(store.current_session.started_at, t_start, places=3)

    def test_save_daemon_type_in_filename(self):
        store, tmpdir = _make_store(daemon_type="builder")
        self.assertIn("builder", store.session_path)

    def test_save_creates_logs_daemon_directory(self):
        _, tmpdir = _make_store()
        store = SessionStore(daemon_type="test", base_dir=tmpdir)
        store.save(cycle_count=0, total_improvements=0)
        self.assertTrue(os.path.isdir(os.path.join(tmpdir, "logs", "daemon")))

    def test_save_no_tmp_file_left_after_success(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        tmp_path = store.session_path + ".tmp"
        self.assertFalse(os.path.exists(tmp_path), ".tmp no debe quedar tras escritura exitosa")


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionStoreLoad
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionStoreLoad(unittest.TestCase):
    """load() maneja todos los casos: sin archivo, corrupto, expirado, válido."""

    def test_load_returns_none_when_no_file(self):
        store, tmpdir = _make_store()
        result = store.load()
        self.assertIsNone(result)

    def test_load_returns_session_after_save(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=7, total_improvements=3)
        store.reset()  # limpia estado en memoria
        result = store.load()
        self.assertIsNotNone(result)
        self.assertEqual(result.cycle_count, 7)
        self.assertEqual(result.total_improvements, 3)

    def test_load_restores_daemon_type(self):
        store, tmpdir = _make_store(daemon_type="guardian")
        store.save(cycle_count=1, total_improvements=0)
        store.reset()
        result = store.load()
        self.assertEqual(result.daemon_type, "guardian")

    def test_load_returns_none_for_corrupted_json(self):
        store, tmpdir = _make_store()
        os.makedirs(os.path.dirname(store.session_path), exist_ok=True)
        with open(store.session_path, "w") as f:
            f.write("{ this is not valid JSON }")
        result = store.load()
        self.assertIsNone(result)

    def test_load_returns_none_for_missing_fields(self):
        store, tmpdir = _make_store()
        os.makedirs(os.path.dirname(store.session_path), exist_ok=True)
        with open(store.session_path, "w") as f:
            json.dump({"session_id": "abc"}, f)  # faltan campos
        result = store.load()
        self.assertIsNone(result)

    def test_load_returns_none_for_expired_session(self):
        store, tmpdir = _make_store(max_age_seconds=5)
        store.save(cycle_count=10, total_improvements=4)
        # Falsificar last_updated_at a 100s atrás
        with open(store.session_path, "r") as f:
            data = json.load(f)
        data["last_updated_at"] = time.time() - 100
        with open(store.session_path, "w") as f:
            json.dump(data, f)
        store.reset()
        result = store.load()
        self.assertIsNone(result)

    def test_load_updates_current_session_in_memory(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=4, total_improvements=1)
        store.reset()
        self.assertIsNone(store.current_session)
        store.load()
        self.assertIsNotNone(store.current_session)

    def test_load_does_not_raise_on_os_error(self):
        """Si el archivo existe pero no es legible, no debe lanzar excepción."""
        store, tmpdir = _make_store()
        os.makedirs(os.path.dirname(store.session_path), exist_ok=True)
        with open(store.session_path, "w") as f:
            f.write("not json at all!!")
        # No debe propagar excepción
        result = store.load()
        self.assertIsNone(result)

    def test_load_two_stores_independent(self):
        """Dos stores de distinto daemon_type no interfieren."""
        s1, tmp1 = _make_store(daemon_type="builder")
        s2, tmp2 = _make_store(daemon_type="guardian")
        s1.save(cycle_count=10, total_improvements=5)
        s2.save(cycle_count=3, total_improvements=1)
        s1.reset()
        s2.reset()
        r1 = s1.load()
        r2 = s2.load()
        self.assertEqual(r1.cycle_count, 10)
        self.assertEqual(r2.cycle_count, 3)


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionStoreClear
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionStoreClear(unittest.TestCase):
    """clear() borra disco; reset() solo limpia memoria."""

    def test_clear_removes_session_file(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        self.assertTrue(os.path.exists(store.session_path))
        store.clear()
        self.assertFalse(os.path.exists(store.session_path))

    def test_clear_sets_current_session_to_none(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=1, total_improvements=0)
        store.clear()
        self.assertIsNone(store.current_session)

    def test_clear_idempotent_when_no_file(self):
        store, tmpdir = _make_store()
        # No debe lanzar excepción si no hay archivo
        store.clear()
        store.clear()

    def test_clear_then_save_creates_new_session(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=10, total_improvements=5)
        sid1 = store.current_session.session_id
        store.clear()
        store.save(cycle_count=1, total_improvements=0)
        sid2 = store.current_session.session_id
        self.assertNotEqual(sid1, sid2, "Un nuevo save post-clear debe generar nuevo session_id")

    def test_reset_does_not_delete_file(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=3, total_improvements=1)
        store.reset()
        self.assertTrue(os.path.exists(store.session_path), "reset() no debe borrar el archivo")

    def test_reset_clears_memory_state(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=3, total_improvements=1)
        self.assertIsNotNone(store.current_session)
        store.reset()
        self.assertIsNone(store.current_session)

    def test_reset_allows_load_from_disk(self):
        store, tmpdir = _make_store()
        store.save(cycle_count=8, total_improvements=4)
        store.reset()
        session = store.load()
        self.assertIsNotNone(session)
        self.assertEqual(session.cycle_count, 8)


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionStoreAtomic
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionStoreAtomic(unittest.TestCase):
    """Escritura atómica — no debe dejar archivos tmp residuales."""

    def test_no_tmp_file_after_successful_write(self):
        store, tmpdir = _make_store()
        for i in range(10):
            store.save(cycle_count=i, total_improvements=i // 2)
        tmp_path = store.session_path + ".tmp"
        self.assertFalse(os.path.exists(tmp_path))

    def test_multiple_saves_overwrite_correctly(self):
        store, tmpdir = _make_store()
        for i in range(5):
            store.save(cycle_count=i, total_improvements=0)
        with open(store.session_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["cycle_count"], 4)  # último valor

    def test_save_load_cycle_consistent(self):
        """Guardar y cargar 3 veces produce valores consistentes."""
        store, tmpdir = _make_store()
        values = [(3, 1), (7, 2), (12, 5)]
        for cycles, improv in values:
            store.save(cycle_count=cycles, total_improvements=improv)
            store.reset()
            session = store.load()
            self.assertEqual(session.cycle_count, cycles)
            self.assertEqual(session.total_improvements, improv)


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionStorePath
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionStorePath(unittest.TestCase):
    """Property session_path devuelve ruta correcta."""

    def test_session_path_includes_daemon_type(self):
        store, _ = _make_store(daemon_type="researcher")
        self.assertIn("researcher", store.session_path)

    def test_session_path_ends_with_json(self):
        store, _ = _make_store()
        self.assertTrue(store.session_path.endswith(".json"))

    def test_session_path_inside_logs_daemon(self):
        _, tmpdir = _make_store()
        store = SessionStore(daemon_type="default", base_dir=tmpdir)
        expected_dir = os.path.join(tmpdir, "logs", "daemon")
        self.assertTrue(store.session_path.startswith(expected_dir))

    def test_different_daemon_types_have_different_paths(self):
        s1, _ = _make_store(daemon_type="builder")
        s2, _ = _make_store(daemon_type="guardian")
        self.assertNotEqual(s1.session_path, s2.session_path)


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionStoreRepr
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionStoreRepr(unittest.TestCase):
    """__repr__ incluye información útil."""

    def test_repr_includes_daemon_type(self):
        store, _ = _make_store(daemon_type="builder")
        self.assertIn("builder", repr(store))

    def test_repr_includes_session_status(self):
        store, _ = _make_store()
        r = repr(store)
        self.assertIn("none", r)
        store.save(cycle_count=1, total_improvements=0)
        r2 = repr(store)
        self.assertIn("yes", r2)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
