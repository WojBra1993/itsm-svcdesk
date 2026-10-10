FROM python:3.13-slim
WORKDIR /capture
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY capture.py spec-attributes.json ./
CMD ["python", "capture.py"]
