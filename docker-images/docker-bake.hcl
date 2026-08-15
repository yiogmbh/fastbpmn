variable "VERSION" {
  default = "0.0.0"
}

variable "REGISTRY" {
  default = "ghcr.io/yiogmbh/fastbpmn"
}

variable "PLATFORMS" {
  default = ["linux/arm64", "linux/amd64"]
}

variable "PYTHON_VERSIONS" {
  default = ["3.11", "3.12", "3.13", "3.14"]
}

variable "OS_VERSIONS_DEBIAN_BASED" {
  default = ["trixie-slim", "trixie"]
}

variable "OS_VERSIONS_ALPINE_BASED" {
  default = ["alpine"]
}

variable "OS_VERSIONS" {
  defalt = concat(
    OS_VERSIONS_DEBIAN_BASED,
    OS_VERSIONS_ALPINE_BASED
  )
}

function "_dockerfile" {
  params = [os]
  result = contains(OS_VERSIONS_ALPINE_BASED, os) ? "docker-images/Dockerfile.alpine" : "docker-images/Dockerfile.debian"
}

function "_version" {
  params = []
  result = trimprefix(VERSION, "v")
}

function "_tags" {
  params = [python, os]
  result = concat(
    [
      "${REGISTRY}:${_version()}-python${python}-${os}",
      "${REGISTRY}:python${python}-${os}",
    ],
    python == "3.14" && os == "trixie-slim" ? ["${REGISTRY}:latest"] : [],
  )
}

target "build" {
  name = "python-${replace(python, ".", "_")}-${os}"
  matrix = {
    python = PYTHON_VERSIONS
    os     = ["trixie-slim", "trixie", "alpine"]
  }
  context    = "."
  dockerfile = _dockerfile(os)
  platforms  = PLATFORMS
  args = {
    UV_IMAGE                = "ghcr.io/astral-sh/uv:python${python}-${os}"
    YIO_fastbpmn_PACKAGE    = "fastbpmn"
    YIO_fastbpmn_VERSION    = VERSION
  }
  tags = _tags(python, os)
}

group "debian" {
  targets = ["python-3_14-trixie-slim"]
}

group "alpine" {
  targets = ["python-3_14-alpine"]
}

group "default" {
  targets = [
    "python-3_11-trixie-slim",
    "python-3_11-trixie",
    "python-3_11-alpine",
    "python-3_12-trixie-slim",
    "python-3_12-trixie",
    "python-3_12-alpine",
    "python-3_13-trixie-slim",
    "python-3_13-trixie",
    "python-3_13-alpine",
    "python-3_14-trixie-slim",
    "python-3_14-trixie",
    "python-3_14-alpine",
  ]
}
