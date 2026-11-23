"""
conftest.py - Pytest Test Isolation Fixtures
Redirects all database and catalog persistence to an isolated temporary directory
via SAKTHI_DATA_DIR, guaranteeing that running tests never modifies production data/heats.db.
"""

import os
import shutil
import tempfile
import pytest


@pytest.fixture(autouse=True, scope="session")
def isolate_test_data_directory():
    """
    Session-scoped autouse fixture that isolates all file and database storage
    inside an ephemeral temporary directory for the duration of the test run.
    """
    temp_dir = tempfile.mkdtemp(prefix="sakthi_test_data_")
    old_env = os.environ.get("SAKTHI_DATA_DIR")
    os.environ["SAKTHI_DATA_DIR"] = temp_dir

    # Force initialization inside the temporary directory
    from backend import storage
    storage.init_grades()
    storage.init_alloys()
    storage.init_db()

    yield temp_dir

    # Cleanup after all tests complete
    if old_env is not None:
        os.environ["SAKTHI_DATA_DIR"] = old_env
    else:
        os.environ.pop("SAKTHI_DATA_DIR", None)
    shutil.rmtree(temp_dir, ignore_errors=True)
