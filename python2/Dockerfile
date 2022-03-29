# this is one of the cached base images available for ACI
FROM python:3.7.4

# Install libraries and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
	
RUN pip3 install --upgrade pip

# Install dependencies
RUN pip3 install -U setuptools \
    && pip3 install git+https://github.com/microsoft/bonsai-common \
    && pip3 uninstall -y setuptools
	
RUN pip3 install matplotlib \
	&& pip3 install pandas \
	&& pip3 install scipy \
	&& pip3 install python-dotenv

#RUN apt install libsdl2-dev

# Set up the simulator
WORKDIR /sim

# Copy simulator files to /sim
COPY ./ /sim

# This will be the command to run the simulator
CMD ["python", "main.py"]
