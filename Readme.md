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
        {
            "host": "db.example.com",
            "upstream": "postgres:5432",
            "type": "tcp"
        }
    ]
}
```

Each route is either HTTP (default; `type` omitted or `"http"`) or raw TCP (`"type": "tcp"`).

For TCP routes:
- The LB does raw TCP pass-through — it never terminates TLS. The backend keeps its own cert and TLS is end-to-end (works for Postgres, MySQL, Mongo, Redis, etc.).
- The LB listens on the same port as the upstream. `postgres:5432` means the LB listens on `:5432` and proxies to `postgres:5432`. You must expose that port in `docker run` (e.g. `-p 5432:5432`).
- One TCP route per port. To expose multiple instances of the same service, run them on different external ports at the backend.
- `host` is a label / DNS name you point at the LB; it is not used for routing (no L4 proxy can route arbitrary TCP by hostname).

# Usage
```bash
docker run  malayh/nginx-lb:2.0 -v /etc/letsencrypt:/etc/letsencrypt -v /etc/nginx/routes:/etc/nginx/routes -p 80:80 -p 443:443
```

Add `-p <port>:<port>` for each TCP route, e.g. `-p 5432:5432` for a Postgres route.