import os

from python_inspector.dependencies import get_extra_data_from_requirements

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQ_FILE = os.path.join(BASE_DIR, "data", "requirements-test.txt")


def test_get_extra_data_from_requirements():
    expected = [
        {
            "extra_index_urls": [
                "https://pypi.python.org/simple/",
                "https://testpypi.python.org/simple/",
                "https://pypi1.python.org/simple/",
            ]
        }
    ]
    result = list(get_extra_data_from_requirements(REQ_FILE))
    assert expected == result
