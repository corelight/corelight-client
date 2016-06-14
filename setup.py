
import sys
import setuptools

if sys.version_info[0] != 3 or sys.version_info[1] < 4:
    sys.exit("brobox currently requires Python >= 3.4")

def readme():
    with open('README.rst') as f:
        return f.read()

setuptools.setup(name='brobox',
    version='1.0',
    description='BroBox API client',
    long_description=readme(),
    url='http://www.broala.com/brobox',
    author='Broala',
    author_email='support@broala.com',
    license='BSD',
    packages=['brobox'],
    zip_safe=False,

    scripts=[
        'bin/brobox'
        ],

    package_data={
        "brobox": [
            "certs/broala-root.pem"
            ]
        },

    install_requires=[
        'requests',
    ],

    classifiers=[
      'License :: OSI Approved :: BSD License',
      'Programming Language :: Python :: 3 :: Only'
    ],
)
