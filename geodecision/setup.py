import os
import sys

from setuptools import setup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import versioneer

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

setup(
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/x-rst",
)
