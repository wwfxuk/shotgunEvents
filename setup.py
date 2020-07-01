import os
import re

from setuptools import setup, find_packages


def get_version():
    """Get version from source file."""
    root = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir))
    daemon_py = os.path.join(root, "src", "shotgunEventDaemon.py")

    with open(daemon_py, "rU") as daemon_file:
        contents = daemon_file.read()
        match = re.search(r'\s*__version__ = [\'"]([^\'"]+)[\'"]', contents)

    return match.group(1)


setup(
    name="shotgunEvents",
    version=get_version(),
    zip_safe=False,
    package_dir={"": "src"},
    py_modules=["shotgunEventDaemon", "daemonizer"],
    entry_points={"console_scripts": ["shotgunEventDaemon=shotgunEventDaemon:main"],},
)
