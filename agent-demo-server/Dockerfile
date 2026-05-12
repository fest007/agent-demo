FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY agent-demo-agent ./agent-demo-agent
RUN uv pip install --system -e ./agent-demo-agent

COPY agent-demo-server ./agent-demo-server
RUN uv pip install --system -e ./agent-demo-server

WORKDIR /app/agent-demo-server

RUN mkdir -p data /app/agent-demo-agent/data/chroma /app/agent-demo-agent/knowledge

EXPOSE 8000

CMD ["python", "-m", "server.main"]
