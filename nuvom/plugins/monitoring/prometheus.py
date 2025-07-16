# nuvom/plugins/monitoring/prometheus.py

"""
Prometheus monitoring plugin for Nuvom.

This plugin exposes runtime metrics over an HTTP endpoint compatible with Prometheus scraping.

Metrics exposed include:
- Active worker thread count
- In-flight job count
- Queue size
- (Planned) Job durations and success/failure counters

It runs a threaded HTTP server and periodically updates metrics using a user-provided
runtime statistics provider. The server exposes metrics on `/metrics`, and a simple
HTML interface on `/` or `/debug`.

Key features:
- Thread-safe, concurrent metric scrapes
- Background refresh loop for real-time updates
- Graceful shutdown support
"""

from __future__ import annotations

import threading
import http.server
import socketserver
import time
from prometheus_client import Gauge, generate_latest
from prometheus_client.core import CollectorRegistry

from nuvom.plugins.contracts import Plugin
from nuvom.log import get_logger

logger = get_logger("plugin")


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP handler for serving Prometheus metrics.

    - `/metrics`: returns the raw Prometheus metrics in text format
    - `/`, `/debug`: returns a human-readable HTML page for manual inspection
    """

    def do_GET(self):
        logger.info(f"[Prometheus] HTTP GET {self.path} from {self.client_address}")
        if self.path == "/metrics":
            output = generate_latest(self.server.registry)
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
        """Suppress default HTTP server logs."""
        return


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    A multi-threaded TCP server that handles each request in a separate thread.
    """
    daemon_threads = True
    allow_reuse_address = True


class PrometheusPlugin(Plugin):
    """
    Prometheus monitoring plugin for Nuvom.

    This plugin starts a threaded HTTP server exposing runtime metrics compatible with Prometheus.
    It uses a background thread to refresh metric values by polling a `metrics_provider` function
    passed at runtime.

    Capabilities:
    - Starts a Prometheus-compatible HTTP server on a configurable port
    - Updates metrics periodically (even without scrapes)
    - Thread-safe request handling
    - Clean shutdown support

    Expected format from metrics_provider():
        {
            "worker_count": int,
            "inflight_jobs": int,
            "queue_size": int
        }
    """

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

    def start(self, settings: dict, **runtime: dict) -> None:
        """
        Start the Prometheus metrics server and background metrics refresh.

        Args:
            settings: Plugin configuration dict (e.g., port number)
            runtime: Runtime-injected resources, including optional metrics_provider
        """
        self.port = settings.get("prometheus_port", 9150)
        self.provider = runtime.get("metrics_provider")

        self.server = ThreadedTCPServer(("", self.port), MetricsHandler)
        self.server.registry = self.registry

        self._server_thread = threading.Thread(target=self._serve_forever, daemon=True)
        self._server_thread.start()

        self._start_refresh_loop()

        logger.info(f"[Prometheus] Exporter started at http://localhost:{self.port}/metrics")

    def _serve_forever(self):
        """
        Run the HTTP server's main loop. Handles requests concurrently and checks
        the shutdown flag at regular intervals.
        """
        try:
            self.server.serve_forever(poll_interval=2)
        except Exception as e:
            logger.exception(f"[Prometheus] Server error: {e}")

    def _start_refresh_loop(self, interval: float = 2.0) -> None:
        """
        Starts a background thread that periodically refreshes metric values.
        
        Args:
            interval: Refresh interval in seconds
        """
        def refresher():
            while not self._shutdown_flag.is_set():
                self._refresh_metrics()
                time.sleep(interval)

        t = threading.Thread(target=refresher, daemon=True)
        t.start()

    def _refresh_metrics(self):
        """
        Poll the metrics_provider and update Prometheus Gauges.
        """
        
        if not self.provider:
            # logger.warning("[Prometheus] No metrics provider set.")
            return

        try:
            stats = self.provider()
            self.worker_count.set(stats.get("worker_count", 0))
            self.inflight_jobs.set(stats.get("inflight_jobs", 0))
            self.queue_size.set(stats.get("queue_size", 0))
        except Exception as e:
            logger.warning(f"[Prometheus] Failed to update metrics: {e}")

    def update_runtime(self, **runtime: dict) -> None:
        """
        Update the metrics provider after plugin has already started.
        
        Args:
            runtime: Dictionary with updated runtime configuration.
        """
        if "metrics_provider" in runtime:
            self.provider = runtime["metrics_provider"]

    def stop(self) -> None:
        """
        Gracefully shut down the Prometheus HTTP server and background threads.
        """
        self._shutdown_flag.set()

        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception as e:
                logger.warning(f"[Prometheus] Failed to stop server cleanly: {e}")

        if self._server_thread:
            self._server_thread.join(timeout=2)
