from setuptools import setup, find_packages


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="quantscraper",
    version="0.8.0",
    description="Scrapes data for the QUANT project.",
    long_description=readme(),  # NB: Only used if upload to PyPi
    url="https://github.com/wacl-york/quant-scraper",
    author="Stuart Lacy",
    author_email="stuart.lacy@york.ac.uk",
    entry_points={
        "console_scripts": [
            "quant_scrape = quantscraper.cli:main",
            "quant_preprocess = quantscraper.daily_preprocessing:main",
            "purpleair_convert = quantscraper.convert_purpleair:main",
            "purpleair_preprocess = quantscraper.preprocess_purpleair:main",
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
        "quantaq @ git+https://github.com/quant-aq/py-quantaq@v0.3.0#egg=quantaq",
    ],
    include_package_data=True,
    license="MIT",
    packages=find_packages(include=["quantscraper", "quantscraper.*"]),
    zip_safe=False,
)
