import pymongo
import pymongo.collection
import bson.objectid
import subprocess
import logging
import requests
import yaml

def read_config(path):
    with open(path, 'r') as f:
        return yaml.load(f, yaml.SafeLoader)

def fetch_wildcard_domains():
    unfiltered_list = requests.get("https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/wildcards.txt").content.decode(encoding="ascii").splitlines()
    final_list = [domain[2:] for domain in unfiltered_list if domain.startswith("*.") and domain.count("*") == 1]

    return final_list

def fetch_new_domains(old_domain_list):
    unfiltered_list = requests.get("https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/domains.txt").content.decode(encoding="ascii").splitlines()
    old_domain_set = set(old_domain_list)
    new_domain_set = set(unfiltered_list)

    return list(new_domain_set.difference(old_domain_set))

def submit_to_db(mongo_collection: pymongo.collection.Collection, subdomain_list):
    
    if len(subdomain_list) == 0:
        return

    documents = [{"value": sub, "parent_program": bson.ObjectId("00"*12)} for sub in subdomain_list]
    try:
        mongo_collection.insert_many(documents, ordered=False)
    except:
        pass

def find_subdomains(wildcard_domain):
    subprocess.run(["subfinder", "-d", wildcard_domain, "-max-time", "15", "-o", "subfinder-output.txt"])

    subdomain_list = []

    try:
        with open("subfinder-output.txt") as file:
            subdomain_list = file.readlines()
            subdomain_list = [s.strip() for s in subdomain_list]
    except:
        return []
    
    return subdomain_list

def main():
    cfg = read_config("config.yaml")
    
    mongo_uri = cfg["mongo"]["uri"]
    mongo_dbname = cfg["mongo"]["db_name"]
    mongo_subdomain_collection_name = cfg["mongo"]["subdomain_collection"]

    mongo_client = pymongo.MongoClient(mongo_uri)
    mongo_subdomain_collection = mongo_client[mongo_dbname][mongo_subdomain_collection_name]

    domain_list = []

    while(True):
        domain_list = fetch_new_domains(domain_list)
        submit_to_db(mongo_subdomain_collection, domain_list)

        wildcard_domain_list = fetch_wildcard_domains()

        for domain in wildcard_domain_list:

            for _ in range(5):
                subs = find_subdomains(domain)
                if len(subs) > 0:
                    break
            
            if len(subs) == 0:
                continue

            submit_to_db(mongo_subdomain_collection, subs)

if __name__ == "__main__":
    main()