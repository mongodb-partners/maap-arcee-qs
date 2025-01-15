FROM downloads.unstructured.io/unstructured-io/unstructured:latest

COPY ./requirements.txt /code/requirements.txt
COPY ./main.py /code/main.py
COPY ./loader.py /code/loader.py
COPY ./utils.py /code/utils.py
COPY ./eventlogging.py /code/eventlogging.py

USER root
# Set up working directory
WORKDIR /code

# Create directories with correct permissions
RUN mkdir -p applogs files && \
    chown -R notebook-user:notebook-user applogs files && \
    chmod 755 applogs files
USER notebook-user

RUN pip install -r requirements.txt

EXPOSE 8001
ENTRYPOINT [ "python3", "main.py" ]