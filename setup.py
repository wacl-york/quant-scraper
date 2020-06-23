from setuptools import setup, find_packages


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="quantscraper",
    version="0.3.0",
    description="Scrapes data for the QUANT project.",
    long_description=readme(),  # NB: Only used if upload to PyPi
    url="https://github.com/wacl-york/QUANTscraper",
    author="Stuart Lacy",
    author_email="stuart.lacy@york.ac.uk",
    entry_points={
        "console_scripts": [
            "quant_scrape = quantscraper.cli:main",
            "quant_preprocess = quantscraper.daily_preprocessing:main",
        ],
    },
    install_requires=[
        "boto3",
        "bs4",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "requests",
        "pandas",
        "python-dotenv",
        "quantaq @ https://github.com/quant-aq/py-quantaq/tarball/master/#egg=0.3.0",
    ],
    include_package_data=True,
    license="MIT",
    packages=find_packages(include=["quantscraper", "quantscraper.*"]),
    zip_safe=False,
)
