from fastapi import FastAPI
import requests
import os
import docker

app = FastAPI()
client = docker.from_env()

PROM_HOST = os.getenv("PROMETHEUS_HOST", "localhost")
PROM_PORT = os.getenv("PROMETHEUS_PORT", "9090")

@app.get("/health")
def health():
    # Container metrics
    containers = client.containers.list()
    containers_running = len(containers)

    # Optionally fetch metrics from host Prometheus
    try:
        prom_resp = requests.get(f"http://{PROM_HOST}:{PROM_PORT}/api/v1/targets")
        prom_data = prom_resp.json()
    except Exception:
        prom_data = None

    return {
        "status": "ok",
        "uptime": "0h 0m",
        "containers_running": containers_running,
        "prometheus_targets": prom_data,
    }

@app.get("/projects")
def projects():
    return [
        {"name": "Homelab Monitoring Stack", "tech": ["Docker", "Prometheus", "Grafana", "Loki"], "description": "Full observability stack running on my server"},
        {"name": "Portfolio Website", "tech": ["FastAPI", "Nginx"], "description": "Personal website hosted on my homelab"},
    ]