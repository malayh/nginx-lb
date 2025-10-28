FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y python3-certbot-nginx nginx jq && \
    apt-get clean;

WORKDIR /etc/nginx
COPY nginx.conf /etc/nginx/nginx.conf
COPY route.template /etc/nginx/route.template
COPY main.sh /etc/nginx/main.sh
RUN chmod +x /etc/nginx/main.sh

CMD ["/etc/nginx/main.sh"]


