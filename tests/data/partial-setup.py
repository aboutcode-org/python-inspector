from setuptools import setup

semver_version = "2.13.0"

setup(
    name="example",
    version="0.0.1",
    install_requires=[
        f"semver @ git+https://github.com/python-semver/python-semver.git@{semver_version}",
    ],
    extras_require={"test": ["botocore==1.27.76"]},
)
