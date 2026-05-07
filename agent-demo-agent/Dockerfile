FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

RUN mkdir -p data/chroma data/memory.db data/long_term.db

EXPOSE 8001

CMD ["python", "-m", "agent.main"]
