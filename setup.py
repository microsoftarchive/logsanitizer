from setuptools import setup, find_packages
import sys, os

version = '0.1.1'

setup(
    name = 'logsanitizer',
    version = version,
    description = "Log processing and sanitizer tool written in Python.",
    packages = find_packages( exclude = [ 'ez_setup'] ),
    include_package_data = True,
    zip_safe = False,
    author = 'Bence Faludi',
    author_email = 'befaludi@microsoft.com',
    license = 'MIT',
    install_requires = [
        'pyyaml'
    ],
    entry_points={
        'console_scripts': [
            'logsanitizer = logsanitizer:main',
        ],
    },
    test_suite = "logsanitizer.tests",
    url = 'http://6wunderkinder.com'
)
