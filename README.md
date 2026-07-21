> ***GeoDecision => Decision-making tools for urban management***

## Presentation
> ***Note** => This package is mainly use - for now - through [dockers](https://github.com/VCityTeam/UD-geodecision-docker)*

Geodecision is a set of tools to help urban decision-making:
* Accessibility/network operations and measures (*graph approach*).
* CityGML parsing to get roofs and measures:
  * slopes
  * area
  * compactness
  * ...
* OSM queries
* Classification (*automatic best classification from data - for example INSEE gridded data*)
* Spatial operations:
  * intersections between GeoDataFrame

Geodecision inputs and outputs are geospatial data:
* [GeoJSON](https://geojson.org/)
* [GeoPackages (an OGC open format)](https://www.geopackage.org/)

## Installation
### Warnings/Disclaimer
> ***/!\ Please read carefully these warnings related to spatial libraries installation***

Our package requires libraries with **spatial functionality** such as [GeoPandas](https://geopandas.org). Such libraries depends on on open source libraries ([GEOS](https://geos.osgeo.org/), [GDAL](https://www.gdal.org/), [PROJ](https://proj.org/)). As written in GeoPandas "*Those **base C libraries can sometimes be a challenge to install**. [...] So depending on your platform, you might need to compile and install their C dependencies manually. [...]. Using conda [...] avoids the need to compile the dependencies yourself.*".

If you want to read more about it, you may want to read the [GeoPandas installation warnings](https://geopandas.org/install.html#installation) and the [blog article on differences between conda and pip](https://www.anaconda.com/understanding-conda-and-pip/). You can also have a look on the table below (*from the just quoted blog article*)

|                       | conda                   | pip                             |
|-----------------------|-------------------------|---------------------------------|
| manages               | binaries                | wheel or source                 |
| can require compilers | no                      | yes                             |
| package types         | any                     | Python-only                     |
| create environment    | yes, built-in           | no, requires virtualenv or venv |
| **dependency checks** | **yes**                 | **no**                          |
| package sources       | Anaconda repo and cloud | PyPI                            |

Regarding these warnings and for **purposes of stability and multi-platform installations**, we choose to use [Conda](https://docs.conda.io/projects/conda/en/latest/) - *an open-source package management system and environment management system* - to install and work with our package. Conda is used massively now and especially in the **data science**, machine learning and AI domains (*it includes most of useful packages such as NumPy, Pandas, ...*) and for **visualization**.

We choose to install it through the creation of a **conda virtual environment** that install and contains all the **required libraries as well as our own package**.

### How to
> ***Disclaimer*** Geodecision is a conda package but not yet available on Anaconda cloud. So the installation must be set from an offline build package.   

#### Install geodecision
##### Current installation process

***/!\ Disclaimer: The installation process is a little bit more complicated from local than from Anaconda cloud. Normally, the build package should have been uploaded on [Anaconda cloud](https://docs.anaconda.com/anaconda-cloud/user-guide/tasks/work-with-packages/#uploading-conda-packages) to be available and easily installable with a simple command ```conda install -c [channel] geodecision```. But this package is still not yet on cloud so we had to make the build package available from a local place. This package is used by [UD-geodecision-docker processes](https://github.com/VCityTeam/UD-geodecision-docker) and the building process of this package could require a few minutes. So it appeared simpler to make build package (Linux, OSX and Windows versions) available in ```geodecision.conda.build``` directory.

1. Get & install conda:
    * [Miniconda](https://docs.conda.io/en/latest/miniconda.html) *=> minimal package*
    * [Anaconda](https://www.anaconda.com/distribution/) *=> includes graphical interface and other tools*
2. Clone or download this repository:
  * Create a conda virtual environment [*Optional but strongly recommended*]:
    ```bash
    conda create --name [myenv]
    ```
3. Open a Command Line Interface inside the cloned repository
4. **Create a directory channel**:
  > *Recommended to use a tmp directory and respect the location of this directory*

  * *command*:
      ```bash
      mkdir -p [path/to/new/directory/channel/arch]
      ```
  * *example*:
      ```bash
      mkdir -p /tmp/my-conda-channel/linux-64
    ```
5. **Copy the build file to the channel & architecture directory**:
    * *command*:
        ```bash
        cp [path/to/tar.bz2/build/file] [path/to/new/directory/channel/arch/]
        ```
    * *example*:
        ```bash
        cp conda.build/linux-64/geodecision-0.1-0.tar.bz2 /tmp/my-conda-channel/linux-64/
        ```
6. **Conda index the channel**:
    * *command*:
        ```bash
        conda index [path/to/new/directory/channel/arch]
        ```
    * *example*:
        ```bash
        conda index /tmp/my-conda-channel/linux-64/
        ```
7. **Conda install from this channel**:
    * *command*:
        ```bash
        conda install -c file:[path/to/new/directory/channel/] [package_name]=[package_version]
        ```
    * *example*:
        ```bash
        conda install -c file://tmp/my-conda-channel/ geodecision=0.1
        ```

##### Moving to cloud
To make this package available from Anaconda cloud, these changes will be required:
* upload build package to [Anaconda cloud](https://docs.anaconda.com/anaconda-cloud/user-guide/tasks/work-with-packages/#uploading-conda-packages)
* remove ```geodecision.conda.build``` directory
* change installation process:
  ```bash
  conda install -c [channel] geodecision
  ```
* update the installation process in [UD-geodecision-docker](https://github.com/VCityTeam/UD-geodecision-docker):
  * Replace:
    ```
    # Create a directory channel
    RUN mkdir -p /tmp/my-conda-channel/linux-64

    # Copy the build file to the channel & architecture directory
    RUN cp UD-geodecision/geodecision/conda.build/linux-64/geodecision-0.1-0.tar.bz2 /tmp/my-conda-channel/linux-64/
    RUN conda install conda-build

    # Index the channel
    RUN conda index /tmp/my-conda-channel/linux-64/

    # Create conda virtual environment
    RUN conda create --name geodecision
    SHELL ["conda", "run", "-n", "geodecision", "/bin/bash", "-c"]

    # Conda install geodecision package
    RUN conda config --append channels conda-forge
    RUN conda install -c file://tmp/my-conda-channel/ geodecision=0.1
    ```
  * By:
    ```
    # Create conda virtual environment
    RUN conda create --name geodecision
    SHELL ["conda", "run", "-n", "geodecision", "/bin/bash", "-c"]

    # Install geodecision
    RUN conda install -c [channel] geodecision
    ```

#### Use it
Once installed, you can use it as other packages:
```python
import geodecision
from geodecision import [specific]
```

#### Try the example
A full worked example — walking accessibility to real OpenStreetMap park polygons, end to end — lives in [`geodecision/examples/`](geodecision/examples/README.md). It runs entirely through the package's own CLI, so no example-only code is needed:

```bash
cd geodecision
pip install -e .
geodecision download-graph        examples/config/graph.json
geodecision fetch-polygons        examples/config/parks.json
geodecision fetch-polygons        examples/config/buildings.json
geodecision compute-accessibility examples/config/accessibility.json
geodecision visualize             examples/config/visualize.json
```

This downloads a walkable street network and real park polygons for a bounding box in Lyon, computes isochrones (walking time to the nearest park), and renders a map to `geodecision/examples/output/isochrones_map.png`. Every parameter — bounding box, projection, trip times, ... — is set in the JSON config files under `examples/config/`, so re-running for a different area is a matter of editing JSON, not code.

See [`geodecision/examples/README.md`](geodecision/examples/README.md) for the full walkthrough, what each output file contains, and which library versions are known to work today (the ones pinned in `env.yml` are from 2020 and no longer installable as-is).

### Architecture
#### Python geodecision module and sub-modules
```
geodecision/
├── accessibility
│   ├── accessibility.py
│   ├── __init__.py
│   ├── isochrone.py
│   └── schema.py
├── citygml
│   ├── analyseroofs.py
│   ├── categories.py
│   ├── constants.py
│   └── __init__.py
├── classification
│   ├── classification.py
│   ├── constants_vars.py
│   └── __init__.py
├── cli.py
├── geodecision.py
├── graph
│   ├── connectpoints.py
│   ├── __init__.py
│   ├── splittednodes.py
│   └── utils.py
├── __init__.py
├── logger
│   ├── __init__.py
│   └── logger.py
├── osmquery
│   ├── __init__.py
│   └── methods.py
└── spatialops
    ├── __init__.py
    └── operations.py
```

## Developer's notes
### Work with geodecision and make changes
> *This method could be compared to the creation of a virtual environment and ```pip install -e``` command*.

### Create a conda virtual environment from ```dev_env.yml``` file
```bash
conda env create -f [path/to/geodecision/dev_env.yml]
```

### Activate this environment
```bash
conda activate dev_env
```

### Install the package (*symbolik link*)
```bash
conda develop [path/to/geodecision]
```

### Structure correctly your modules and submodules
#### A good structuration
Our conda geodecision package is structured like this (*see below*) and you have to respect this organisation if you want to add your own modules and submodules.
```
 geodecision:
    |--- AUTHORS.rst
    |--- CONTRIBUTING.rst
    |--- dev_env.yml
    |--- HISTORY.rst
    |--- Makefile
    |--- MANIFEST.in
    |--- README.rst
    |--- requirements_dev.text
    |--- setup.cfg
    |--- setup.py
    |--- tox.ini
    |--- .editorconfig
    |--- .gitignore
    |___ conda.recipe
    |    |--- meta.yml
    |___ docs
    |    |--- authors.rst
    |    |--- conf.py
    |    |--- contributing.rst
    |    |--- history.rst
    |    |--- index.rst
    |    |--- installation.rst
    |    |--- make.bat
    |    |--- Makefile
    |    |--- modules.rst
    |    |--- readme.rst
    |    |--- usage.rst
    |___ geodecision
    |     ├── accessibility
    |     │   ├── accessibility.py
    |     │   ├── __init__.py
    |     │   ├── isochrone.py
    |     │   └── schema.py
    |     ├── citygml
    |     |      │   └── __init__.py
    |     │   ├── analyseroofs.py
    |     │   ├── categories.py
    |     │   ├── constants.py
    |     │   └── __init__.py
    |     ├── classification
    |     │   ├── classification.py
    |     │   ├── constants_vars.py
    |     │   └── __init__.py
    |     ├── cli.py
    |     ├── geodecision.py
    |     ├── graph
    |     │   ├── connectpoints.py
    |     │   ├── __init__.py
    |     │   ├── splittednodes.py
    |     │   └── utils.py
    |     ├── __init__.py
    |     ├── logger
    |     │   ├── __init__.py
    |     │   └── logger.py
    |     ├── osmquery
    |     │   ├── __init__.py
    |     │   └── methods.py
    |     └── spatialops
    |         ├── __init__.py
    |         └── operations.py
    |___ tests
    |    |--- __init__.py
    |    |--- test_mymodule.py
    |___ .github
```

If you already have module and sub-modules, put them in:
```
mymodule
    |___ mymodule
```
Once done, don't forget to check if the ```import``` are done in the right way. Let's say you have this architecture;
```
mymodule
    |___ mymodule
         |--- cli.py
         |--- __init__.py
         |--- mymodule.py
         |___ submoduleA
         |    |--- __init__.py
         |    |--- submoduleAOne
         |    |--- submoduleATwo
         |___ submoduleB
              |--- __init__.py
              |--- submoduleBOne
              |--- submoduleBTwo
```
If you want ***class OneA***  from ```submoduleAOne``` and ***class TwoB*** from ```submoduleBTwo``` to be accessible from your module, you need to edit the ```__init__.py```:
```
mymodule
    |___ mymodule
         |--- __init__.py
```
You have to add these lines:
```python
from .submoduleA.submoduleAOne import OneA
from .submoduleB.submoduleBTwo import TwoB
```

If you want to import ***class OneB*** from ```submoduleBOne``` in ```submoduleATwo``` you need to add this line in ```submoduleATwo```:
```python
from ..submoduleB.submoduleBOne import OneB
```

### Build after changes
> *[Follow the process described in this documentation](https://github.com/VCityTeam/UD-SV/blob/master/UD-Doc/Devel/BuildCondaPackage.md) and make the necessary changes/adaptations*

### Documentation
> We use [Sphinx](http://www.sphinx-doc.org/) for documentation

#### Generate documentation with Sphinx
> ***/!\ If you use the [numpydoc docstrings](https://numpydoc.readthedocs.io/en/latest/format.html#), add the [napoleon sphinx extension](http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) in ```conf.py```***:
```
mymodule:
   |___ docs
        |--- conf.py
```
```python
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.napoleon']
```

Then generate documentation with command lines. Start a command line inside ```docs``` repository:
```
sphinx-apidoc -f -o . ../mymodule/
```
It will generate a bunch of ***rst*** files. Then, to get ***html*** pages (*in a ```_build``` directory for example*):
```
cd ..
sphinx-build -b html docs/ _build/
```
