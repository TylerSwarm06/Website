from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
import docker
from docker.errors import DockerException

app = FastAPI(title="Portfolio API", version="0.1.0")

origins = [
    "https://tylerswarm.com",
    "https://www.tylerswarm.com",
    "http://localhost",
    "http://127.0.0.1",
    "http://192.168.1.179",
    "http://192.168.1.179:4545",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_start_time = time.time()

PROJECTS = [
    {
        "name": "Portfolio Website",
        "description": "My personal portfolio site built with FastAPI and Nginx.",
        "tech": ["FastAPI", "Docker", "Nginx", "JavaScript"],
    },
    {
        "name": "Homelab Infrastructure",
        "description": "Monitoring, networking, and containerized services in my homelab.",
        "tech": ["Prometheus", "Grafana", "Docker", "Linux"],
    },
]

CORE_SERVICE_RULES = [
    {
        "matchers": ["cloudflared"],
        "key": "cloudflare-tunnel",
        "group": "edge",
        "label": "Cloudflare Tunnel",
        "url": None,
        "depends_on": ["nginx-proxy-manager"],
        "connects_to": ["nginx-proxy-manager"],
    },
    {
        "matchers": ["nginx-proxy-manager", "npm"],
        "key": "nginx-proxy-manager",
        "group": "edge",
        "label": "Nginx Proxy Manager",
        "url": None,
        "depends_on": [],
        "connects_to": ["portfolio-frontend", "portfolio-api"],
    },
    {
        "matchers": ["portfolio-frontend"],
        "key": "portfolio-frontend",
        "group": "application",
        "label": "Portfolio Frontend",
        "url": "https://tylerswarm.com",
        "depends_on": ["portfolio-api"],
        "connects_to": ["portfolio-api"],
    },
    {
        "matchers": ["portfolio-backend"],
        "key": "portfolio-api",
        "group": "application",
        "label": "Portfolio API",
        "url": "https://api.tylerswarm.com",
        "depends_on": ["docker-socket"],
        "connects_to": ["prometheus", "loki"],
    },
    {
        "matchers": ["prometheus"],
        "key": "prometheus",
        "group": "observability",
        "label": "Prometheus",
        "url": None,
        "depends_on": [],
        "connects_to": ["grafana"],
    },
    {
        "matchers": ["grafana"],
        "key": "grafana",
        "group": "observability",
        "label": "Grafana",
        "url": None,
        "depends_on": ["prometheus", "loki"],
        "connects_to": [],
    },
    {
        "matchers": ["loki"],
        "key": "loki",
        "group": "observability",
        "label": "Loki",
        "url": None,
        "depends_on": [],
        "connects_to": ["grafana"],
    },
]


def format_duration(total_seconds: float) -> str:
    total_seconds = int(total_seconds)
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def get_api_uptime() -> str:
    return format_duration(time.time() - api_start_time)


def get_host_uptime() -> str:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            uptime_seconds = float(f.read().split()[0])
        return format_duration(uptime_seconds)
    except Exception:
        return "Unavailable"


def get_docker_client():
    try:
        return docker.from_env()
    except DockerException:
        return None
    except Exception:
        return None


def infer_service_metadata(container_name: str):
    lowered = container_name.lower()
    for rule in CORE_SERVICE_RULES:
        if any(matcher in lowered for matcher in rule["matchers"]):
            return {
                "key": rule["key"],
                "group": rule["group"],
                "label": rule["label"],
                "url": rule["url"],
                "depends_on": rule["depends_on"],
                "connects_to": rule["connects_to"],
            }
    return None


def derive_service_status(container) -> tuple[str, str]:
    state = container.attrs.get("State", {})
    docker_state = state.get("Status", "unknown")
    health_obj = state.get("Health")
    health_status = health_obj.get("Status") if health_obj else None

    derived_status = "down"

    if docker_state == "running":
        derived_status = "healthy"
    elif docker_state in ("restarting", "paused", "created"):
        derived_status = "degraded"

    if health_status == "healthy":
        derived_status = "healthy"
    elif health_status == "unhealthy":
        derived_status = "down"
    elif health_status == "starting":
        derived_status = "degraded"

    return derived_status, docker_state


def get_service_summary():
    client = get_docker_client()
    if client is None:
        return {
            "docker_available": False,
            "containers_running": None,
            "healthy": None,
            "degraded": None,
            "down": None,
            "services": [],
        }

    try:
        all_containers = client.containers.list(all=True)
        running_containers = client.containers.list()

        services = []
        healthy = 0
        degraded = 0
        down = 0

        for container in all_containers:
            meta = infer_service_metadata(container.name)
            if meta is None:
                continue

            derived_status, docker_state = derive_service_status(container)

            if derived_status == "healthy":
                healthy += 1
            elif derived_status == "degraded":
                degraded += 1
            else:
                down += 1

            services.append(
                {
                    "key": meta["key"],
                    "name": container.name,
                    "label": meta["label"],
                    "group": meta["group"],
                    "status": derived_status,
                    "docker_state": docker_state,
                    "url": meta["url"],
                    "depends_on": meta["depends_on"],
                    "connects_to": meta["connects_to"],
                }
            )

        group_order = {"edge": 0, "application": 1, "observability": 2}
        services.sort(key=lambda s: (group_order.get(s["group"], 99), s["label"].lower()))

        return {
            "docker_available": True,
            "containers_running": len(running_containers),
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "services": services,
        }
    except Exception:
        return {
            "docker_available": False,
            "containers_running": None,
            "healthy": None,
            "degraded": None,
            "down": None,
            "services": [],
        }


@app.get("/")
def root():
    return {"message": "Portfolio API is running"}


@app.get("/api/health")
def health():
    service_summary = get_service_summary()
    return {
        "status": "ok",
        "api_reachable": True,
        "api_uptime": get_api_uptime(),
        "host_uptime": get_host_uptime(),
        "containers_running": service_summary["containers_running"],
        "docker_available": service_summary["docker_available"],
        "service_health": {
            "healthy": service_summary["healthy"],
            "degraded": service_summary["degraded"],
            "down": service_summary["down"],
        },
        "prometheus_targets": None,
        "timestamp": int(time.time()),
    }


@app.get("/api/projects")
def projects():
    return PROJECTS


@app.get("/api/services")
def services():
    service_summary = get_service_summary()
    return {
        "docker_available": service_summary["docker_available"],
        "containers_running": service_summary["containers_running"],
        "service_health": {
            "healthy": service_summary["healthy"],
            "degraded": service_summary["degraded"],
            "down": service_summary["down"],
        },
        "services": service_summary["services"],
        "timestamp": int(time.time()),
    }