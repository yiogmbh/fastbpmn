# Docker

fastbpmn publishes pre-built Docker images for multiple Python versions, operating system bases, and architectures.

You can use these images to have a solid foundation for your process automation needs.

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

**Recommended — build all variants with Docker Bake:**

!!! tip "Local usage"
    If you want to use the images locally, it is usually required to limit the build to at least a single platform,
    as multi platform images are not yet supported to export / load directly to local docker.

    To achieve this, two override files are provided:

    - `docker-bake.override.amd64.hcl` for the `linux/amd64` platform
    - `docker-bake.override.arm64.hcl` for the `linux/arm64` platform



```shell
docker buildx bake \
  -f docker-images/docker-bake.hcl \
  --var VERSION=$(git describe --tags --always) \
  default
```

Build only debian / alpine images (`python3.14`):

```shell
# debian
docker buildx bake \
  -f docker-images/docker-bake.hcl
  --var VERSION=$(git describe --tags --always) \
  debian

# alpine
docker buildx bake \
  -f docker-images/docker-bake.hcl
  --var VERSION=$(git describe --tags --always) \
  alpine
```

Build a single variant:

```shell
docker buildx bake \
  -f docker-images/docker-bake.hcl \
  --var VERSION=$(git describe --tags --always) \
  python-3_14-alpine
```
