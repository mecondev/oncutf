from types import SimpleNamespace

from oncutf.utils import path_utils
from oncutf.utils.path_normalizer import normalize_path


def test_normalize_and_paths_equal():
    p1 = "C:/folder\\sub/f.txt"
    p2 = "C:\\folder/sub/f.txt"
    assert normalize_path(p1) == normalize_path(p2)
    assert path_utils.paths_equal(p1, p2)


def test_find_file_by_path():
    obj = SimpleNamespace(full_path="/home/user/file.txt")
    res = path_utils.find_file_by_path([obj], "/home/user\\file.txt")
    assert res is obj


def test_get_resource_dirs():
    # Should return Path objects (existence not required in test)
    assert path_utils.get_project_root() is not None
    assert path_utils.get_resources_dir().name == "resources"


def test_paths_equal_edge_cases():
    assert path_utils.paths_equal("", "")
    assert not path_utils.paths_equal("", "/a")
    assert path_utils.paths_equal("/a/b/", "/a/b")
