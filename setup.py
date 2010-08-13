from setuptools import setup, find_packages
import sys, os

version = '0.5'

readme = open('README.txt').read()
changes = open("CHANGES.txt").read()

description = """
%s

Changes
=======

%s""" % (readme, changes)


setup(name="libopencore",
      version=version,
      description="a library of functions for connecting external apps to/from opencore",
      long_description=description,
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
        "httplib2",
        "ElementTree",
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
        "twirlip": [
            "eyvind",
            "signedheaders",
            "transcluder",
            ]
        },
      entry_points="""
      [paste.app_factory]
      proxy = libopencore.http_proxy:app_factory

      [paste.composite_factory]
      main = libopencore.wsgi:composite_factory

      [paste.filter_factory]
      deliverance = libopencore.deliverance_middleware:filter_factory
      transcluder = libopencore.transcluder_middleware:create_transcluder
      """,
      )
