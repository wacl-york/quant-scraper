from setuptools import setup


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="quantscraper",
    version="0.1",
    description="Scrapes data for the QUANT project.",
    long_description=readme(),  # NB: Only used if upload to PyPi
    url="https://github.com/wacl-york/QUANTscraper",
    author="Stuart Lacy",
    author_email="stuart.lacy@york.ac.uk",
    scripts=["bin/quantscrape.py"],
    install_requires=[
        "requests",
        "pandas",
        "quantaq @ https://github.com/quant-aq/py-quantaq/tarball/master/#egg=0.3.0",
    ],
    # dependency_links=["https://github.com/quant-aq/py-quantaq/tarball/master/#egg=0.3.0"],
    include_package_data=True,
    license="MIT",
    packages=["quantscraper"],
    zip_safe=False,
)
