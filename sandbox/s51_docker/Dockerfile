FROM python:3.10-slim-bookworm@sha256:db6ee5170ebce0f4d165af242e8e77addc08bd9ffc37e8b1815752cf027aa4f8
ARG MLFLOW_VERSION
LABEL org.pafta.lesson="ai-saldiri-51"
RUN test "$MLFLOW_VERSION" = "2.1.1" || test "$MLFLOW_VERSION" = "2.2.1"
RUN python -m pip install --no-cache-dir --report /opt/pafta-pip-report.json "mlflow==$MLFLOW_VERSION" "Flask==2.2.5" "Werkzeug==2.2.3" "numpy==1.24.4" "pandas==1.5.3" "pyarrow==10.0.1" "SQLAlchemy==1.4.54" "setuptools==69.5.1"
RUN python -m pip freeze > /opt/pafta-packages.txt
COPY server.py /opt/pafta-server.py
USER 10001:10001
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /tmp
CMD ["python","/opt/pafta-server.py"]
