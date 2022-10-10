import os

name = f"dittobot-duelapi-{os.getpid()}"
bind = f"{os.getenv('GUNICORN_HOST', '0.0.0.0')}:{os.getenv('GUNICORN_PORT', '5864')}"
worker_class = "uvicorn.workers.UvicornWorker"
workers = 8
threads = 3
loglevel = "warning"
errorlog = "-"
