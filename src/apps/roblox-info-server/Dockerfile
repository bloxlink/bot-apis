FROM python:3.10.4

WORKDIR /usr/src/bloxlink-info-server

ADD . /usr/src/bloxlink-info-server

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 7002

ENTRYPOINT ["python3", "src/main.py"]