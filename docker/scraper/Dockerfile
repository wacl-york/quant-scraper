# Have gone with ubuntu (debian buster) rather than alpine
# Alpine doesn't have toolchain and needs to compile numpy from scratch, which is so far taking ~15 minutes on my work laptop, and will likely take up a large amount of storage, thereby negating advantage of using Debian image
# Alpine ~300MB? guess based on SO posts.
# Debian ~1.1GB
FROM python:3.7-buster
WORKDIR /quantscraper
COPY ./ ./
RUN mkdir -p data/raw
RUN mkdir -p data/clean
RUN mkdir -p data/analysis
RUN mkdir -p data/availability
RUN python -m pip install --upgrade pip
RUN pip install .

ENTRYPOINT ["python", "docker/scraper/entry.py"]
