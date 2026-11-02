import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "unix:/run/gunicorn/shop_pc.sock")
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_class = "gthread"
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

accesslog = "/var/log/shop_pc/gunicorn_access.log"
errorlog = "/var/log/shop_pc/gunicorn_error.log"
loglevel = "info"
capture_output = True

