# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../'))


# -- Project information -----------------------------------------------------

project = 'Vivarium'
copyright = '2020, Covert Lab'
author = 'Covert Lab'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_rtd_theme',
    'sphinx.ext.todo',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinxcontrib.bibtex',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '_build', 'Thumbs.db', '.DS_Store', 'venv', 'venv_*']

# Causes warnings to be thrown for all unresolvable references. This
# will help avoid broken links.
nitpicky = True


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Options for extensions --------------------------------------------------

# -- sphinx.ext.intersphinx options --
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'matplotlib': ('https://matplotlib.org/3.2.2/', None),
    'shapely': ('https://shapely.readthedocs.io/en/latest/', None),
}

# -- sphinx.ext.autodic options --
autodoc_inherit_docstrings = False
# The Python dependencies aren't really required for building the docs
autodoc_mock_imports = [
    'arpeggio', 'cobra', 'confluent_kafka', 'matplotlib',
    'mpl_toolkits', 'networkx', 'parsimonious', 'pygame', 'pymongo',
    'arrow'
]
# Concatenate class and __init__ docstrings
autoclass_content = 'both'
