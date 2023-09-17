#!venv/bin/python
from multiprocessing import cpu_count
from os import getenv

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    config = uvicorn.Config(
        "main:app",
        host="127.0.0.1",
        port=int(getenv("LEMMY_SEE_MY_HATERS_PORT", 8000)),
        log_level="info",
        workers=cpu_count(),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    server = uvicorn.Server(config)
    server.run()
