FROM python:3.6-alpine as builder

RUN apk update && apk add build-base python-dev py-gevent

RUN mkdir /build
WORKDIR /build
COPY . /build
RUN pip install --install-option="--prefix=/install" .


FROM python:3.6-alpine

COPY --from=builder /install /usr/local

RUN addgroup -g 1000 -S app && \
    adduser -u 1000 -S app -G app
USER app

EXPOSE 15353/tcp
EXPOSE 15353/udp

CMD ["/usr/local/bin/dns-tls-proxy"]
