# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import wsgi_status

with open('README.rst') as f:
    readme = f.read()

setup(
    name='wsgi_status',
    version=wsgi_status.__version__,

    description='Monitoring wsgi status as an upper wsgi middleware',
    long_description=readme,
    author='kizkoh',
    author_email='mac-daisuki@live.com',
    license='MIT',
    install_requires=['psutil'],
    url='https://github.com/kizkoh/wsgi_status',
    packages=find_packages(exclude=('examples', 'tests', 'docs')),
    include_package_data=True,
    test_suite='tests'
)
