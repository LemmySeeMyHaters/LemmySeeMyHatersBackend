#!venv/bin/python
from multiprocessing import cpu_count

import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", port=8000, log_level="info", workers=cpu_count())
    server = uvicorn.Server(config)
    server.run()
