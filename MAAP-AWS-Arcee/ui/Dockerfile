FROM python:3.10-slim

COPY requirements.txt /code/requirements.txt
COPY ./main.py /code/main.py
COPY .env /code/.env

EXPOSE 7860

WORKDIR /code

RUN pip install -r requirements.txt

ENTRYPOINT [ "gradio", "main.py" ]