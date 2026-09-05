import pytest

from python_inspector.dependencies import get_dependency

@pytest.mark.parametrize(
    "text",
    ['Demo==1.2; sys_platform == "Windows Server"', "Demo @ https://example.org/Release/Demo.whl"],
)
def test_dependency_preserves_requirement_text(text):
    dependency = get_dependency("  " + text + "  ")
    assert dependency.extracted_requirement == text
    assert dependency.purl.startswith("pkg:pypi/demo")
