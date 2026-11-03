FROM ghcr.io/astral-sh/uv:python3.11-trixie-slim

RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

WORKDIR /
COPY example.py /example.py

ENTRYPOINT ["uv", "run"]
CMD ["/example.py"]
