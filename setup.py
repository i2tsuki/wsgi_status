# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

setup(
    name='wsgi_status',
    version='0.1.0',

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
