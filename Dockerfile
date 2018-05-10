FROM python:2.7.13-alpine

COPY app /opt/prometheus-rds-enhanced-exporter
COPY metrics.yaml /opt/prometheus-rds-enhanced-exporter

RUN pip install -r /opt/prometheus-rds-enhanced-exporter/requirements.txt

EXPOSE 9158

CMD ["/bin/sh", "-c", "python /opt/prometheus-rds-enhanced-exporter/exporter.py /config/config.yaml /opt/prometheus-rds-enhanced-exporter/metrics.yaml"]
