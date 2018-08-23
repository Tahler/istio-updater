FROM ubuntu:bionic AS builder

RUN apt-get update
RUN apt-get install -y curl

WORKDIR /tmp

# Install kubectl
RUN curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/v1.10.4/bin/linux/amd64/kubectl
RUN chmod +x kubectl
RUN mv kubectl /usr/local/bin/kubectl

# Install helm
RUN curl -Lo helm.tar.gz https://storage.googleapis.com/kubernetes-helm/helm-v2.7.2-linux-amd64.tar.gz
RUN tar zxf helm.tar.gz
RUN mv linux-amd64/helm /usr/local/bin/helm

FROM python:3.5

COPY --from=builder /usr/local/bin/kubectl /usr/local/bin/kubectl
COPY --from=builder /usr/local/bin/helm /usr/local/bin/helm

COPY . .

RUN pip3 install -r requirements.txt

ENTRYPOINT [ "./main.py" ]
