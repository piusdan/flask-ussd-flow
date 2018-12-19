"""
Flask-USSDFlow
-------------

a Flask microframework extension which helps
you build fast USSD applications by defining USSD screens
in JSON
"""
from setuptools import setup


setup(
    name='Flask-USSDFlow',
    version='0.1',
    url='#',
    license='BSD',
    author='Pius Dan Nyongesa',
    author_email='npiusdan@gmail.com',
    description='Helps your build fast USSD applications',
    long_description=__doc__,
    packages=['flask_ussd_flow'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask>=0.10',
        'requests>=2.21.0',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)