FROM python:3.12-slim
WORKDIR /app
COPY server.py .
USER 65534
EXPOSE 8000
CMD ["python", "-I", "-u", "server.py"]
