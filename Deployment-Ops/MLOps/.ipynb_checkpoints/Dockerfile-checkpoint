FROM ubuntu:20.04

# Install Miniconda
RUN apt-get update && apt-get install -y wget libgl1-mesa-glx libglib2.0-0
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
RUN bash miniconda.sh -b -p /opt/conda
ENV PATH="/opt/conda/bin:${PATH}"

# Copy and create Conda environment
COPY environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml

# Activate the Conda environment
# RUN conda init
# RUN conda activate sagemaker_env
COPY blockhouse_ml /home/blockhouse_ml
COPY requirements.txt /home/requirements.txt
COPY README.md /home/README.md
COPY setup.py /home/setup.py

ENV PATH="/opt/conda/envs/sagemaker_env/bin:${PATH}"

# Set up SageMaker-specific configurations
# ENV SAGEMAKER_PROGRAM train.py

# Copy your training script
# COPY train.py /opt/ml/code/train.py

WORKDIR /opt/ml/code
RUN pip install -e .