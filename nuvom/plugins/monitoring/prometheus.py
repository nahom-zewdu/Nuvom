# nuvom/plugins/monitoring/prometheus.py

"""
Prometheus monitoring plugin.

Exposes runtime metrics like:
• Current worker count
• In-flight job count
• Queue size
• Success/failure counters
• Job durations

Runs a non-blocking HTTP server exposing metrics on /metrics.
"""

from __future__ import annotations

import threading
import time
import http.server
import socketserver
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry

from nuvom.plugins.contracts import Plugin

class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            output = generate_latest(self.registry)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)

        elif self.path in ("/", "/debug"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><head><title>Nuvom Metrics</title></head><body>")
            self.wfile.write(b"<h1>Nuvom Prometheus Exporter</h1>")
            self.wfile.write(b"<p>This exporter exposes internal runtime stats for Prometheus scraping.</p>")
            self.wfile.write(b"<ul>")
            self.wfile.write(b"<li><a href='/metrics'>/metrics</a> - raw Prometheus output</li>")
            self.wfile.write(b"</ul>")
            self.wfile.write(b"</body></html>")

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return  # Suppress default logging

class PrometheusPlugin(Plugin):
    api_version = "1.0"
    name = "prometheus"
    provides = ["monitoring"]
    requires = []

    def __init__(self) -> None:
        self._server_thread: threading.Thread | None = None
        self._shutdown_flag = threading.Event()
        self.port: int = 9150
        self.registry = CollectorRegistry()
        self.server: socketserver.TCPServer | None = None
        self.provider = None

        # Exposed metrics
        self.worker_count = Gauge("nuvom_worker_count", "Number of active worker threads", registry=self.registry)
        self.inflight_jobs = Gauge("nuvom_inflight_jobs", "Current in-flight job count", registry=self.registry)
        self.queue_size = Gauge("nuvom_queue_size", "Size of the job queue", registry=self.registry)
        # self.job_duration = Histogram("nuvom_job_duration_seconds", "Job execution time (seconds)", registry=self.registry)
        # self.job_success = Counter("nuvom_job_success_total", "Total successful jobs", registry=self.registry)
        # self.job_failure = Counter("nuvom_job_failure_total", "Total failed jobs", registry=self.registry)

    def start(self, settings: dict, **runtime: dict) -> None:
        self.port = settings.get("prometheus_port", 9150)

        # Optional runtime metrics provider
        self.provider = runtime.get("metrics_provider")

        handler = type("CustomHandler", (MetricsHandler,), {"registry": self.registry})
        self.server = socketserver.TCPServer(("", self.port), handler)

        self._server_thread = threading.Thread(target=self._serve_forever, daemon=True)
        self._server_thread.start()
    
    def update_runtime(self, **runtime: dict) -> None:
        """Update runtime metrics provider after plugin has started."""
        if "metrics_provider" in runtime:
            self.provider = runtime["metrics_provider"]

    def _serve_forever(self):
        while not self._shutdown_flag.is_set():
            try:
                self.server.handle_request()
                self._refresh_metrics()
            except Exception:
                print(Exception)
                continue  # Resilience

    def _refresh_metrics(self):
        if not self.provider:
            print("no provider")
            return

        try:
            stats = self.provider()
            self.worker_count.set(stats.get("worker_count", 0))
            self.inflight_jobs.set(stats.get("inflight_jobs", 0))
            self.queue_size.set(stats.get("queue_size", 0))

        except Exception:
            pass

    def stop(self) -> None:
        self._shutdown_flag.set()
        if self.server:
            try:
                self.server.server_close()
            except Exception:
                pass
        if self._server_thread:
            self._server_thread.join(timeout=2)
