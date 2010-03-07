from setuptools import setup, find_packages
import sys, os

version = '0.1'

readme = open('README.txt').read()

setup(name="libopencore",
      version=version,
      description="library functions for connecting external apps to/from opencore",
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
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
