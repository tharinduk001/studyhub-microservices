FROM --platform=linux/amd64 python:3.13.3-bookworm

ENV PYTHONBUFFERED=1

WORKDIR /simply

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY . .

CMD python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000