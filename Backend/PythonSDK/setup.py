from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = "1.0.11"
DESCRIPTION = "Blockhouse SDK"
LONG_DESCRIPTION = (
    "A package that allows to get technical analysis using the Blockhouse API"
)

setup(
    name="blockhouse",
    version=VERSION,
    author="Blockhouse Labs",
    author_email="<mail@blockhouse.com>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    install_requires=["requests"],#, "boto3", "json"],
    keywords=[
        "python",
        "blockhouse",
        "sdk",
        "stock",
        "market",
        "trading",
        "algotrading",
        "finance",
        "financial",
        "stocks",
        "market",
        "data",
        "api",
        "wrapper",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
)
