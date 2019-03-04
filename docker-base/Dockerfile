FROM python:3.7-alpine3.8
RUN echo "https://mirror.tuna.tsinghua.edu.cn/alpine/v3.8/main/" > /etc/apk/repositories
RUN apk update \
    && apk upgrade \
    && apk add --no-cache --virtual .build-deps build-base libffi-dev gmp-dev libressl-dev \
    && apk add --no-cache zeromq-dev \
    && apk add --no-cache bash \
    && pip3 install zmq \
    && pip3 install pymysql \
    && pip3 install bs4 \
    && pip3 install python-bitcoinrpc \
    && pip3 install eth \
    && pip3 install ethereum \
    && pip3 install web3 \
    && apk del .build-deps \
    && rm -rf /var/cache/apk/*
CMD /bin/sh
