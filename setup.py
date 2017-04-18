# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='wsgi_status',
    version='0.1.0',
    description='Monitoring status wsgi upper middleware',
    long_description=readme,
    author='kizkoh',
    author_email='mac-daisuki@live.com',
    install_requires=['psutil'],
    url='https://github.com/kizkoh/wsgi_status',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
    test_suite='tests'
)
