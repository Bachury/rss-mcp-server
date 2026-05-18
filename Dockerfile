FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Apply nest_asyncio before any Python code runs, so that even if the
# runtime (e.g. Horizon's with-proxy-runner / fastmcp CLI) calls
# asyncio.run() inside an already-running event loop, it won't crash.
RUN python -c "import site; print(site.getsitepackages()[0])" \
    | xargs -I{} sh -c 'echo "import nest_asyncio; nest_asyncio.apply()" > {}/sitecustomize.py'

COPY . .

EXPOSE 8081

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8081"]
