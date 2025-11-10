def pytest_configure(config):
    """
    Ensure the repository root is at the front of sys.path so package-relative
    imports (e.g. ``tests.test_dicom_mcp``) succeed no matter how pytest is
    invoked.
    """
    import importlib
    import sys
    from pathlib import Path

    repo_root = str(Path(__file__).resolve().parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Prime the ``tests`` package so that ``import tests.test_*`` works even if
    # another module named ``tests`` was imported earlier by the runtime.
    if "tests" not in sys.modules:
        try:
            importlib.import_module("tests")
        except ModuleNotFoundError:
            pass
    if "tests" in sys.modules:
        mod = sys.modules["tests"]
        print("debug: configure tests module ->", getattr(mod, "__file__", None), getattr(mod, "__path__", None))

