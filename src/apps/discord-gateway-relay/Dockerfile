FROM python:3.10.1

WORKDIR /usr/src/discord-relay

ADD . /usr/src/discord-relay

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt


ENTRYPOINT ["python3", "src/main.py"]