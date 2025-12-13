FROM debian:bullseye

USER root

RUN apt-get update && apt-get install -y \
    build-essential git vim \
    python3 python3-pip
RUN python3 -m pip install cython pytest
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN g++ -v

WORKDIR /IMCtermite
COPY ./ .

# install CLI tool
RUN make install

# install Python module
RUN make python-build

CMD ["sleep","infinity"]
