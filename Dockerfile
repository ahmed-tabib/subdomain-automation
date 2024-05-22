FROM python:3.9

WORKDIR /subdomain-automation

COPY . .

RUN pip install pymongo pyyaml requests
RUN chmod +x /subdomain-automation/subfinder && ln -s /subdomain-automation/subfinder /usr/bin

CMD ["python", "startup.py"]
