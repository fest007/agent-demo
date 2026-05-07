FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

RUN mkdir -p data

EXPOSE 8000

CMD ["python", "-m", "server.main"]
