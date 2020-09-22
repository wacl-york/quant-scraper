FROM python:3.7-buster
WORKDIR /quantscraper
ADD . ./
RUN mkdir -p data/raw
RUN mkdir -p data/clean
RUN mkdir -p data/analysis
RUN mkdir -p data/availability
RUN python -m pip install --upgrade pip
RUN pip install .

ENTRYPOINT ["python", "docker/purpleair/entry.py"]
