# tests/test_plugins/test_prometheus.py

import time
import threading
import requests
import socket
import pytest

from nuvom.plugins.monitoring.prometheus import PrometheusPlugin

# ------------------------
# Utility: Find free port
# ------------------------
def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

# ------------------------
# Fixture: Plugin Instance
# ------------------------
@pytest.fixture
def prometheus_plugin():
    port = get_free_port()
    plugin = PrometheusPlugin()
    plugin.start({"prometheus_port": port}, metrics_provider=lambda: {
        "worker_count": 4,
        "inflight_jobs": 2,
        "queue_size": 10
    })

    yield plugin, port

    plugin.stop()
    time.sleep(0.3)  # Give thread time to clean up

# ------------------------
# Test: /metrics returns 200
# ------------------------

def test_metrics_endpoint_responds(prometheus_plugin):
    plugin, port = prometheus_plugin
    url = f"http://localhost:{port}/metrics"

    for _ in range(5):
        try:
            r = requests.get(url)
            assert r.status_code == 200
            assert "text/plain" in r.headers["Content-Type"]
            assert "nuvom_worker_count" in r.text
            break
        except Exception:
            time.sleep(0.2)
    else:
        pytest.fail("/metrics endpoint did not respond correctly")

# ------------------------
# Test: Metrics values reflect provider
# ------------------------

def test_metrics_values_correct(prometheus_plugin):
    plugin, port = prometheus_plugin
    url = f"http://localhost:{port}/metrics"

    plugin._refresh_metrics()  # Force immediate update

    r = requests.get(url)
    body = r.text

    assert "nuvom_worker_count 4.0" in body
    assert "nuvom_inflight_jobs 2.0" in body
    assert "nuvom_queue_size 10.0" in body


# ------------------------
# Test: Update runtime provider after start
# ------------------------

def test_runtime_provider_update():
    port = get_free_port()
    plugin = PrometheusPlugin()

    plugin.start({"prometheus_port": port})  # No provider yet

    def later_provider():
        return {"worker_count": 9, "inflight_jobs": 3, "queue_size": 99}

    plugin.update_runtime(metrics_provider=later_provider)
    
    plugin._refresh_metrics()  # <-- Force immediate update
    
    r = requests.get(f"http://localhost:{port}/metrics")

    assert "nuvom_worker_count 9.0" in r.text
    assert "nuvom_inflight_jobs 3.0" in r.text
    assert "nuvom_queue_size 99.0" in r.text

    plugin.stop()

# ------------------------
# Test: /debug and root respond with HTML
# ------------------------

def test_debug_and_root_endpoints(prometheus_plugin):
    _, port = prometheus_plugin
    for path in ["/", "/debug"]:
        r = requests.get(f"http://localhost:{port}{path}")
        assert r.status_code == 200
        assert "text/html" in r.headers["Content-Type"]
        assert "Prometheus Exporter" in r.text

# ------------------------
# Test: Invalid path returns 404
# ------------------------

def test_invalid_path_returns_404(prometheus_plugin):
    _, port = prometheus_plugin
    r = requests.get(f"http://localhost:{port}/doesnotexist")
    assert r.status_code == 404
