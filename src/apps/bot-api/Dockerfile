FROM python:3.10.1

WORKDIR /usr/src/bot-api

ADD . /usr/src/bot-api

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 8002

ENTRYPOINT ["python3", "src/main.py"]