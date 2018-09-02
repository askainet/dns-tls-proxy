# DNS to DNS-over-TLS proxy

Implement a DNS to DNS-over-TLS proxy.

Initial requirements are:

- Handles at least one client sendind queries to the proxy using TCP.
- Forwards query to nameserver using DNS-over-TLS.
- Sends the reply back to the client.

## Extra features

### UDP listener

An UDP listener has been also implemented.

### Allow multiple clients

Multiple concurrent clients are supported by both the TCP and UDP listeners.

### SERVFAIL reply on errors

When the proxy finds some unrecoverable error forwarding the request to the
nameservers (timeouts, unvalid DNS message, etc) it will reply with SERVFAIL
rcode to the client.

### Handle big DNS messages

DNS messages bigger than a single frame are handle properly, both for TCP and
UDP listeners.

### Proxy basic stats

Basic stats to have some performance information about queries per second and
average latency have been added.

### Connection pool to nameservers

Keep a pool of connections to nameservers to try to reuse them, in order to
improve query speed by reducing the number of times an expensive TCP + TLS
handshake is needed when forwarding a DNS query.

It also features:

- Automatic reconnection when lost.
- Temporary blacklisting of problematic nameservers.

### gevent based implementation

My first implementation was done using [socketserver](https://docs.python.org/3.6/library/socketserver.html)
but it comes at a high cost of managing hundreds of clients, creating a
dedicated thread per request.

For a more efficient and lightweight management of multiple concurrent clients
and connections to nameservers, I adapted it to be event loop based using
[gevent](http://www.gevent.org/).

## Questions

### Security concerns

The use of TLS to encrypt DNS helps in protecting privacy, but does not resolve
other potential security issues inherent to DNS. Privacy would be subject to
trusting the TLS-enabled DNS provider.

TLS itself is subject to some specific attacks, like man-in-the-middle and
protocol downgrade.

Clients falling back to other non-TLS resolvers when the DNS-over-TLS is not
working will lose any privacy protection for thos requests.

Some basic measures have been implemented in this application:

- The application forces the use of TLS version 1.2 only.

- This implementation verifies that the hostname configured for the nameserver
matches the one in the server SSL certificate.

- It also verifies that the server certificate is signed by a CA present in the
system store. As the applciation trusts this local system CA store, risks of
tampering with it must be removed.

#### The Dockerfile

The Dockerfile provided to run the proxy uses the Alpine Linux image. It
provides updated CA certificates for DigiCert, GoDaddy and Let's Encrypt, which
are the CAs for the CloudFlare, cleanbrowsing.org and dns.quad9.net nameservers
respectively, used in the examples section.

It also uses a non-root user to run the proxy in order to minimize risks in case
of vulnerabilities.

A multi-layered build configuration removes uneeded software like gcc from the
final image.

### Integration in microservice architecture

The proxy could be used as a service running on every host, and configuring the
OS resolver to use it as the nameserver, so applications running on the host
will use it to resolve DNS names.

However, the lack of caching will generate too much innecessary queries and
latency. Therefore, a much better solution would be to place the proxy after
a caching service like dnsmasq. Applications will use the caching DNS forwarder,
and the forwarder will use the DNS-over-TLS proxy.

In the particular case of Kubernetes, the DNS-over-TLS proxy could be used as a
custom upstream nameserver. The dnsmasq DNS cache service, part of the
cluster-wide kube-dns service, will then use the DNS-over-TLS proxy to resolve
any domain different from the cluster suffix. Pods should be configured with
the `dnsPolicy` set to `ClusterFist` to benefit from this.

### Other possible improvements

- Add tests to code! This was overlooked because of time constrains and in favor
of adding features.

- Better validation of DNS messages.

- Add caching of DNS queries, although this is probably best suited to a more
robust and battle-tested tool like dnsmasq.

- Better network IO and exceptions handling.

- Implement AXFR support.

- Use Go instead of Python for better performance and smaller footprint.

## Configuration

All configurations options are available both as command line arguments and
environment variables:

```
  -n <nameserver>:<port>:<CN-verify>, --nameserver <nameserver>:<port>:<CN-verify>
                        Set the nameservers to forward DNS over TLS queries.
                        Use it multiple times to add more nameservers [env
                        var: NAMESERVERS]
  -l LOGFILE, --logfile LOGFILE
                        Set a logfile instead of using STDERR [env var:
                        LOGFILE]
  -v, --verbose         Enable verbose logging [env var: VERBOSE]
  -d, --debug           Enable debug logging [env var: DEBUG]
  -t, --tcp             Enable TCP listener [env var: ENABLE_TCP]
  -u, --udp             Enable UDP listener [env var: ENABLE_UDP]
  -s, --stats           Enable stats logging [env var: ENABLE_STATS]
  -p PORT, --port PORT  Port number to listen on for DNS queries [env var:
                        PORT]
  --pool-size POOL_SIZE
                        Size of the nameservers connection pool [env var:
                        POOL_SIZE]
```

## Examples

### Command line execution

```
dns-tls-proxy \
    -n 9.9.9.9:853:dns.quad9.net \
    -n 149.112.112.112:853:dns.quad9.net \
    -n 1.1.1.1:853:cloudflare-dns.com \
    -n 1.0.0.1:853:cloudflare-dns.com \
    -n 185.228.168.168:853:cleanbrowsing.org \
    -n 185.228.168.169:853:cleanbrowsing.org
```

### Running with Docker

```
docker run \
    -e NAMESERVERS=1.1.1.1:853:cloudflare-dns.com,9.9.9.9:853:dns.quad9.net \
    -p 15353:15353/udp \
    -p 15353:15353/tcp \
    askainet/dns-tls-proxy
```

### Performance

More than 1k queries per second can be achieved using several concurrent
clients with both UDP and TCP listeners and big enough nameservers pool (using
just a home DSL connection):

```
docker run -it \
    -e NAMESERVERS=9.9.9.9:853:dns.quad9.net,149.112.112.112:853:dns.quad9.net,1.1.1.1:853:cloudflare-dns.com,1.0.0.1:853:cloudflare-dns.com \
    -e POOL_SIZE=40 \
    -p 15353:15353/udp \
    -p 15353:15353/tcp \
    askainet/dns-tls-proxy

...

2018-09-03 00:53:38,374 - WARNING - MainThread: --- Stats of the proxy: #requests 28772 / qps 1400.24 / avg_time 38.39ms
2018-09-03 00:53:38,374 - WARNING - MainThread: --- Stats of UDP listener: #requests 16018 / qps 699.72 / avg_time 40.05ms
2018-09-03 00:53:38,375 - WARNING - MainThread: --- Stats of TCP listener: #requests 12754 / qps 700.52 / avg_time 36.72ms
```

### Big DNS messages

```
dig @127.0.0.1 -p 15353 txt test-size.askai.net

; <<>> DiG 9.12.2-P1 <<>> @127.0.0.1 -p 15353 txt test-size.askai.net
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 30216
;; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1452
; PAD (120 bytes)
;; QUESTION SECTION:
;test-size.askai.net.       IN  TXT

;; ANSWER SECTION:
test-size.askai.net.    3594    IN  TXT "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
test-size.askai.net.    3594    IN  TXT "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

;; Query time: 37 msec
;; SERVER: 127.0.0.1#15353(127.0.0.1)
;; WHEN: Mon Sep 03 00:31:49 CEST 2018
;; MSG SIZE  rcvd: 4212
```
