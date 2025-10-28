# Nginx Load balancer
Simple load nginx load balancer with certbot built in.

# Config
```json
{
    "email": "john@exampl.com",
    "resolver": "127.0.0.11",
    "routes": [
        {
            "host": "website.com",
            "upstream": "http://backend:3000"
        },
    ]
}
```

# Usage
```bash
docker run  malayh/nginx-lb:2.0 -v /etc/letsencrypt:/etc/letsencrypt -v /etc/nginx/routes:/etc/nginx/routes -p 80:80 -p 443:443
```