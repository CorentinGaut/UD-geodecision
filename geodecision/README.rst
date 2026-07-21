   **GeoDecision => Decision-making tools for urban management**

Presentation
------------

   **Note**\ *=> This package is mainly use - for now -
   through*\ `dockers <https://github.com/VCityTeam/UD-geodecision-docker>`__

..

   **TODO**

Installation
------------

Our package requires libraries with **spatial functionality** such as
`GeoPandas <https://geopandas.org>`__. Those depend on open source C
libraries (`GEOS <https://geos.osgeo.org/>`__,
`GDAL <https://www.gdal.org/>`__, `PROJ <https://proj.org/>`__), but the
underlying Python packages (``shapely``, ``fiona``, ``pyproj``,
``rtree``) now ship prebuilt wheels bundling these libraries on PyPI, so
no separate compiler or system install is required.

We use `uv <https://docs.astral.sh/uv/>`__ - *an extremely fast Python
package and project manager* - to install and work with our package.

How to
~~~~~~

Install geodecision environment (*containing geodecision package*)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Get & install `uv <https://docs.astral.sh/uv/getting-started/installation/>`__
2. Clone or download this repository
3. Open a Command Line Interface inside the cloned repository
4. Create the virtual environment and install GeoDecision and its
   dependencies: ``bash  uv sync``

Use it
^^^^^^

1. Once installation is done, run commands inside the environment with
   ``bash  uv run geodecision --help``, or activate the virtual
   environment directly: ``bash  source .venv/bin/activate``
2. You can use your IDE, Jupyter notebooks, *etc* … inside this
   environment.

Architecture
~~~~~~~~~~~~

Python geodecision module and sub-modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   geodecision/
   ├── accessibility
   │   ├── accessibility.py
   │   ├── __init__.py
   │   ├── isochrone.py
   │   └── schema.py
   ├── bokeh_snippets
   │   ├── bokeh_snippets.py
   │   └── __init__.py
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

Features
--------

   **TODO**

*To know more*
^^^^^^^^^^^^^^

-  `uv <https://docs.astral.sh/uv/>`__ documentation
-  `Cookiecutter <https://cookiecutter.readthedocs.io/en/latest/>`__ to
   easily create Python packages. *The package was created with
   Cookiecutter and
   the*\ `audreyr/cookiecutter-pypackage <https://github.com/audreyr/cookiecutter-pypackage>`__.
