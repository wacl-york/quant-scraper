from setuptools import setup, find_packages


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
    entry_points={"console_scripts": ["quantscrape = quantscraper.cli:main",],},
    install_requires=[
        "requests",
        "pandas",
        "quantaq @ https://github.com/quant-aq/py-quantaq/tarball/master/#egg=0.3.0",
    ],
    include_package_data=True,
    license="MIT",
    packages=find_packages(include=["quantscraper", "quantscraper.*"]),
    zip_safe=False,
)
