"""Sphinx configuration for the LandProductivity documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "LandProductivity"
author = "Matteo J. Riva"
copyright = "2024, Matteo J. Riva"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

autodoc_mock_imports = ["ee"]

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

html_theme = "sphinx_rtd_theme"
html_static_path = []

exclude_patterns = ["_build"]
