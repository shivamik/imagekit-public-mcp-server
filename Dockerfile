FROM --platform=linux/arm64 python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.0 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/

EXPOSE 8080

CMD ["/bin/bash", "-c", "source /app/.venv/bin/activate && python -m src.lambda_handler"]
