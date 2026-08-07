# Docker

fastbpmn publishes pre-built Docker images for multiple Python versions, operating system bases, and architectures.

## Available images

Images are published to `ghcr.io/yiogmbh/fastbpmn` with the following tag scheme:

```
ghcr.io/yiogmbh/fastbpmn:<version>-python<X.Y>-<os>
ghcr.io/yiogmbh/fastbpmn:python<X.Y>-<os>
```

| Python | OS base | Example tag |
|---|---|---|
| 3.11 | trixie-slim, trixie, alpine | `ghcr.io/yiogmbh/fastbpmn:1.0.0-python3.11-trixie-slim` |
| 3.12 | trixie-slim, trixie, alpine | `ghcr.io/yiogmbh/fastbpmn:1.0.0-python3.12-alpine` |
| 3.13 | trixie-slim, trixie, alpine | `ghcr.io/yiogmbh/fastbpmn:python3.13-trixie` |
| 3.14 | trixie-slim, trixie, alpine | `ghcr.io/yiogmbh/fastbpmn:python3.14-trixie-slim` |

All images are built for both `linux/amd64` and `linux/arm64`.

The `python<X.Y>-<os>` tags (without a version prefix) always point to the latest fastbpmn release for that Python/OS combination.

`:latest` points to the latest stable Python version on Debian trixie-slim.

## Using an image

```dockerfile
FROM ghcr.io/yiogmbh/fastbpmn:1.0.0-python3.13-trixie-slim

COPY ./my-app /home/fastbpmn/app
```

The container exposes no ports by default. It runs `squirrel run` as the entrypoint, looking for an application at `/home/fastbpmn/app/app.py`.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MODULE_NAME` | `app.app` | Python module path for the worker application |
| `VARIABLE_NAME` | `app` | Variable name within the module |
| `PYTHONPATH` | (appended) | Additional Python path entries |

## Building locally

```shell
docker build \
  --build-arg UV_IMAGE=ghcr.io/astral-sh/uv:python3.13-trixie-slim \
  --build-arg YIO_fastbpmn_PACKAGE=fastbpmn \
  --build-arg YIO_fastbpmn_VERSION=$(git describe --tags --always) \
  -f docker-images/Dockerfile \
  -t fastbpmn:local \
  .
```
