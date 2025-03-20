FROM python:3.12-slim

WORKDIR /app

COPY consumer.py requirements.txt ./

RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]
