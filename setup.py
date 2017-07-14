
import sys
import setuptools

if sys.version_info[0] != 3 or sys.version_info[1] < 4:
    sys.exit("brobox currently requires Python >= 3.4")

def readme():
    with open('README.rst') as f:
        return f.read()

setuptools.setup(name="brobox-client",
    version="1.0.5",
    description="BroBox API client",
    long_description=readme(),
    url="https://github.com/corelight/brobox-client",
    author="Corelight",
    author_email="info@corelight.com",
    license="BSD",
    packages=["brobox"],
    zip_safe=False,

    scripts=[
        "bin/brobox"
        ],

    package_data={
        "brobox": [
            "certs/corelight.pem"
            ]
        },

    install_requires=[
        # 2.17.{1,2} have a problem with urrllib3:
        # https://github.com/requests/requests/issues/4104
        "requests>=2.9.1,!=2.17.1,!=2.17.2",
    ],

    classifiers=[
      "License :: OSI Approved :: BSD License",
      "Programming Language :: Python :: 3 :: Only"
    ],
)
