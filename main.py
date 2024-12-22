import time
import argparse
import logging
from pydantic import BaseModel
import yaml
import pathlib
import subprocess
import re
from datetime import datetime, timedelta
import pytz

CONFIG = None
ROUTE_CONFIG_TEMPLATE = """
server {{
    
    server_name {host};
    charset     utf-8;
    # max upload size
    client_max_body_size 75M;
    
    location / {{
        proxy_pass {upstream};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""


logging.basicConfig(
    format="[%(levelname)s]:%(name)s:%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO
)
logger = logging.getLogger("nginx-lb")


class Route(BaseModel):
    host: str
    upstream: str
    tls: bool

class Config(BaseModel):
    email: str
    routesDir: str
    routes: list[Route]

    def verify(self):
        hosts = [route.host for route in self.routes]
        if len(set(hosts)) != len(hosts):
            raise ValueError("All hosts must be unique")

    @classmethod
    def from_config_file(cls, config_file_path: str):
        logger.info(f"Reading config from {config_file_path}")
        with open(config_file_path, "r") as f:
            config_file = yaml.safe_load(f)
            _config = Config(**config_file)
            _config.verify()
            logger.info(f"Config: {_config}")

        return _config


def get_certificates(host: str) -> dict | None:
    command = ["certbot", "certificates", "-d", host]

    # # For testing
    # _s = """
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Found the following certs:
    # Certificate Name: thehazarika.com
    #     Serial Number: 4701d57ebe42947be409a1bb86e270989ee
    #     Key Type: RSA
    #     Domains: thehazarika.com
    #     Expiry Date: 2025-02-25 06:41:42+00:00 (VALID: 64 days)
    #     Certificate Path: /etc/letsencrypt/live/thehazarika.com/fullchain.pem
    #     Private Key Path: /etc/letsencrypt/live/thehazarika.com/privkey.pem
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # """
    # command = ["echo",f"\"{_s}\""]


    process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    output, error = process.communicate()

    if process.returncode != 0:
        logger.error(f"Failed to get certificates for {host}")
        return None
    
    cert_pattern = re.compile(r'Certificate Name:\s+(.*)')
    domain_pattern = re.compile(r'Domains:\s+(.*)')
    expiry_pattern = re.compile(r'Expiry Date:\s+(.*)')

    cert_info = {}
    for line in output.splitlines():
        cert_match = cert_pattern.search(line)
        domain_match = domain_pattern.search(line)
        expiry_match = expiry_pattern.search(line)

        if cert_match:
            cert_info['certificate_name'] = cert_match.group(1).strip()
        elif domain_match:
            cert_info['domains'] = domain_match.group(1).strip()
        elif expiry_match:
            cert_info['expiry'] = expiry_match.group(1).strip()

    
    if not cert_info:
        logger.error(f"No certificates found for {host}")
        return None


    # convert expiry to datetime
    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{2}:\d{2})', cert_info.get('expiry',''))
    if not match:
        logger.error(f"Failed to parse expiry date for {host}")
        return None
    
    cert_info['expiry'] = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S%z")
    logger.info(f"Certificates for {host}: {cert_info}")
    return cert_info


def create_nginx_config():
    global CONFIG

    config_dir = pathlib.Path(CONFIG.routesDir)
    if not config_dir.exists() or not config_dir.is_dir():
        raise ValueError(f"Config dir {config_dir} does not exist or is not a directory")
    
    for route in CONFIG.routes:
        config_file = config_dir.joinpath(f"{route.host}.conf")
        if config_file.exists():
            logger.info(f"Config file {config_file} already exists")
            continue

        with open(config_file, "w") as f:
            f.write(ROUTE_CONFIG_TEMPLATE.format(host=route.host, upstream=route.upstream))
            logger.info(f"Config file {config_file} created")

def start_nginx():
    command = ["nginx", "-g", "daemon off;"]
    subprocess.Popen(command)

def renew_certificates(route: Route):
    global CONFIG

    renew_command = ["certbot","--nginx","-q","renew", "-d", route.host]
    process = subprocess.Popen(renew_command, stdout=subprocess.PIPE, text=True)
    process.wait()
    if process.returncode != 0:
        logger.error(f"Failed to renew certificate for {route.host}")
        return

    reload_command = ["nginx", "-s", "reload"]
    process = subprocess.Popen(reload_command, stdout=subprocess.PIPE, text=True)
    process.wait()
    if process.returncode != 0:
        logger.error(f"Failed to reload nginx after renewing certificate for {route.host}")
        return

    logger.info(f"Renewed tls certificates for {route.host}") 
    
    

def get_new_certificates(route: Route):
    global CONFIG

    get_command = ["certbot", "--nginx", "--agree-tos", "--non-interactive", "-m", CONFIG.email, "-d", route.host]
    process = subprocess.Popen(get_command, stdout=subprocess.PIPE, text=True)
    process.wait()
    if process.returncode != 0:
        logger.error(f"Failed to get certificate for {route.host}")
        return
    
    reload_command = ["nginx", "-s", "reload"]
    process = subprocess.Popen(reload_command, stdout=subprocess.PIPE, text=True)
    process.wait()
    if process.returncode != 0:
        logger.error(f"Failed to reload nginx after getting certificate for {route.host}")
        return
    
    logger.info(f"Get tls certificates for {route.host}")




def renew_or_get_certificates():
    global CONFIG

    for route in CONFIG.routes:
        if not route.tls:
            logger.info(f"TLS not enabled for {route.host}")
            continue

        cert = get_certificates(route.host)
        if not cert:
            logger.info(f"Failed to get certificates for {route.host}")
            get_new_certificates(route)
            continue

        if cert['expiry'] < datetime.now(pytz.UTC) + timedelta(days=15):
            logger.info(f"Certificates for {route.host} are expiring soon, renewing...")
            renew_certificates(route)
            continue

        logger.info(f"Certificates for {route.host} are valid till {cert['expiry']}. Renewal not required")
        

def main():
    global CONFIG

    parser = argparse.ArgumentParser(description="nginx proxy with build-in let's encrypt support")
    parser.add_argument("--config", type=str, help="Path to the config file", required=True)

    args = parser.parse_args()
    CONFIG = Config.from_config_file(args.config)

    logger.info("Starting nginx-lb...")

    create_nginx_config()
    start_nginx()
    
    # TODO: Wait for nginx to start
    try:
        while True:
            renew_or_get_certificates()
            time.sleep(60*60*24)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down gracefully...")



if __name__ == "__main__":
    main()
