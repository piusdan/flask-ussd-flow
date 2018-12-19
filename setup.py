"""
Flask-USSDFlow
-------------

a Flask microframework extension which helps
you build fast USSD applications by defining USSD screens
in JSON
"""
import re
from setuptools import setup


def find_version(fname):
    """Attempts to find the version number in the file names fname.
    Raises RuntimeError if not found.
    """
    version = ""
    with open(fname, "r") as fp:
        reg = re.compile(r'__version__ = [\'"]([^\'"]*)[\'"]')
        for line in fp:
            m = reg.match(line)
            if m:
                version = m.group(1)
                break
    if not version:
        raise RuntimeError("Cannot find version information")
    return version


__version__ = find_version("flask_ussd_flow/__init__.py")


def read(fname):
    with open(fname) as fp:
        content = fp.read()
    return content


setup(
    name="Flask-USSDFlow",
    version="0.1",
    url="https://github.com/Piusdan/flask-ussd-flow",
    license="BSD",
    author="Pius Dan Nyongesa",
    author_email="npiusdan@gmail.com",
    description="Helps your build fast USSD applications",
    long_description=read("README.md"),
    packages=['flask_ussd_flow'],
    zip_safe=False,
    include_package_data=True,
    platforms="any",
    install_requires=["Flask>=0.10", "requests>=2.21.0"],
    extras_require={
        "dev": [
            "pytest==3.7.2",
            "coverage==4.5.0",
            "flake8==3.5.0",
            "pre-commit==1.10.5",
        ]
    },
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
)
