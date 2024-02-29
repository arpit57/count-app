# Use an official Python runtime as a parent image
FROM python:3.8.10

# Set the working directory in the container
WORKDIR /usr/src/countApp/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    curl \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    python-openssl \
    git \
    libcairo2-dev \
    libgirepository1.0-dev \
    pkg-config \
    python3-dev \
    librsync-dev \
    libsystemd-dev \
    libcups2-dev \
    libgl1-mesa-glx \
 && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /usr/src/app
COPY . /usr/src/countApp

# Install Python packages and fix jwt/PyJWT if needed
RUN pip install wheel && \
    pip install -r /usr/src/countApp/requirements.txt && \
    pip uninstall -y jwt PyJWT && \
    pip install PyJWT && \
    pip uninstall -y bson pymongo && \
    pip install pymongo==3.13.0

# Define the command to run your application
CMD ["python3", "main.py"]

