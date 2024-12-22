# Nginx Load balancer
Simple load nginx load balancer with certbot built in.

# Config
```yaml
# Email to be used with letsencrypt
email: test@gmail.com
# Don't change this. Mount this directory to the container to keep the configs
routesDir: /etc/nginx/routes
routes:
    # Host name
  - host: "test.example.com"
    # Enable tls
    tls: true
    # Upstream server
    upstream: "http://services:8080" 
```

# Usage
```bash
docker run  malayh/nginx-lb:1.0.0 \
-v /etc/letsencrypt:/etc/letsencrypt \
-v /etc/nginx/routes:/etc/nginx/routes \
-p 80:80 -p 443:443 \
```