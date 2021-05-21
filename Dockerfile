FROM python:3

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# create directories within container
# /script is where the package lives
ENV SCRIPT_DIR=/script
WORKDIR ${SCRIPT_DIR}

# copy script into container
COPY ./menagerie/ .

# run script by default
ENTRYPOINT ["python3", "/script/plan_ngs_prep.py"]