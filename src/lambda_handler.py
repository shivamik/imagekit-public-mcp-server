"""
Lambda entry point using AWS Lambda Web Adapter.
The Lambda Web Adapter layer forwards requests to the local uvicorn server.
This file starts the ASGI app for use in the Lambda container.
"""

import uvicorn


def main():
    from .server import app  # noqa: F401

    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
