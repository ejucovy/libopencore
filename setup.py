from setuptools import setup, find_packages
import sys, os

version = '0.2'

readme = open('README.txt').read()

setup(name="libopencore",
      version=version,
      description="a library of functions for connecting external apps to/from opencore",
      long_description=readme,
      classifiers=[],
      keywords='',
      author='Ethan Jucovy',
      author_email='opencore-dev@lists.coactivate.org',
      url='',
      license='GPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        ],
      extras_require={
        "deliverance": [
            "Deliverance",
            "WebOb",
            "WSGIProxy",
            "setuptools",
            ],
        "proxy": [
            "WSGIFilter",
            ],
        },
      entry_points="""
      [paste.app_factory]
      proxy = libopencore.http_proxy:app_factory

      [paste.composite_factory]
      main = libopencore.wsgi:composite_factory

      [paste.filter_factory]
      deliverance = libopencore.deliverance_middleware:filter_factory
      """,
      )
