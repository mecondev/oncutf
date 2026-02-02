from oncutf.utils.shared.json_config_manager import (
    FileHashConfig,
    JSONConfigManager,
    WindowConfig,
)


def test_register_save_load(tmp_path):
    cfg_dir = tmp_path / "cfg"
    mgr = JSONConfigManager(app_name="testapp", config_dir=str(cfg_dir))

    # Register categories and modify some values
    win = WindowConfig()
    fh = FileHashConfig()
    mgr.register_category(win)
    mgr.register_category(fh)

    win.set("last_folder", "/tmp")
    fh.add_file_hash("/tmp/a.txt", "abcd1234", 123)

    assert mgr.save()

    # Ensure file exists
    cfg_file = cfg_dir / "config.json"
    assert cfg_file.exists()

    # Load into a fresh manager pointing to same dir
    mgr2 = JSONConfigManager(app_name="testapp", config_dir=str(cfg_dir))
    mgr2.register_category(WindowConfig())
    mgr2.register_category(FileHashConfig())
    assert mgr2.load()

    w2 = mgr2.get_category("window")
    f2 = mgr2.get_category("file_hashes")
    assert w2.get("last_folder") == "/tmp"
    entry = f2.get_file_hash("/tmp/a.txt")
    assert entry is not None and entry.get("tag") == "abcd1234"


def test_get_category_create(tmp_path):
    mgr = JSONConfigManager(app_name="testx", config_dir=str(tmp_path))
    cat = mgr.get_category("dialogs", create_if_not_exists=True)
    assert cat is not None
    assert cat.name == "dialogs"
