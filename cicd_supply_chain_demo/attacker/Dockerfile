FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY exfil_server.py .
EXPOSE 8000
CMD ["python", "exfil_server.py"]
