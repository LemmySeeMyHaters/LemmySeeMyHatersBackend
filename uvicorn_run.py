#!venv/bin/python
from multiprocessing import cpu_count
from os import getenv

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", port=int(getenv("LEMMY_SEE_MY_HATERS_PORT", 8000)), log_level="info", workers=cpu_count())
    server = uvicorn.Server(config)
    server.run()
