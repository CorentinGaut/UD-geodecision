from setuptools import setup, find_packages
import versioneer

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

setup(
    name="geodecision",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Short description",
    license="Proprietary",
    author="thomas",
    author_email="thomleysens@gmail.com",
    long_description=readme + "\n\n" + history,
    url="https://github.com/VCityTeam/UD-geodecision",
    packages=find_packages(include=["geodecision", "geodecision.*"]),
    install_requires=[
			"bokeh>=1.4",
			"fiona",
			"geopandas>=0.6.0",
			"geojson>=2.4.1",
			"geopy>=1.20.0",
			"jsonschema>=3.2.0",
			"mapclassify>=2.1.1",
			"matplotlib",
			"networkx>=2.3",
			"numpy>=1.17.3",
			"osmnx>=2.0.0",
			"pandas>=1.0.0",
			"pyproj>=2.4.2.post1",
			"rtree>=0.9.3",
			"shapely>=1.6.4"
		     ],
    entry_points={
        "console_scripts": [
            "geodecision=geodecision.cli:main",
        ],
    },
    keywords="geodecision",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
