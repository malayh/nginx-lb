FROM python:3.10.15-slim-bookworm

RUN apt-get update && \
    apt-get install -y procps python3-certbot-nginx nginx && \
    apt-get clean;

RUN mkdir /app;
WORKDIR /app;

COPY requirements.txt main.py .
COPY nginx.conf /etc/nginx/nginx.conf
RUN pip install -r requirements.txt;

ENTRYPOINT ["python", "main.py"]
CMD ["--config", "/app/config.yaml"]
