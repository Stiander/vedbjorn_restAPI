FROM python:3.10-slim-buster

LABEL IMAGE="rest"

RUN adduser --disabled-password --gecos '' --shell /bin/bash rest && \
    usermod -aG sudo,staff rest && \
    apt update && apt install -y --no-install-recommends sudo && \
    apt install ffmpeg libsm6 libxext6  -y && \
    echo "rest ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/10-rest && \
    chown rest:rest /usr/local/bin/pip

WORKDIR /home/rest

COPY --chown=rest:rest requirements.txt .

ENV PATH="/home/rest/.local/bin:${PATH}"
ENV GOOGLE_APPLICATION_CREDENTIALS=vedbjorn-eeec629a3cbc.json
#ENV PORT=8080
#ENV QRPC_HOST=vedbjorn-grpc-server-36aidthlda-lz.a.run.app
#ENV QRPC_PORT=443

USER rest

RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir --user -r requirements.txt

COPY --chown=rest:rest src/ .

RUN sudo rm -f /etc/sudoers.d/10-rest

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
#CMD [ "python", "-u", "./main.py" ]