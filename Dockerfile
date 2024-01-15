FROM python:3.9

WORKDIR /subdomain-automation

COPY . .

RUN pip install pymongo pyyaml requests
RUN ln -s /subdomain-automation/subfinder /usr/bin

CMD ["python", "startup.py"]