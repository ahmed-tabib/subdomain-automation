import pymongo
import pymongo.collection
import bson.objectid
import subprocess
import logging
import requests
import yaml
import json

def read_config(path):
    with open(path, 'r') as f:
        return yaml.load(f, yaml.SafeLoader)

def domain_program_has_bounties(domain, hackerone_programs, intigriti_programs, bugcrowd_programs):
    
    for program in hackerone_programs:
        for asset in program['targets']['in_scope']:
            if domain in asset['asset_identifier'] and asset['asset_type'] in ['WILDCARD', 'URL']:
                return (program['offers_bounties'], program['url'])
    
    for program in intigriti_programs:
        for asset in program['targets']['in_scope']:
            if domain in asset['endpoint']:
                return ((program['max_bounty']['value'] > 0), program['url'])
    
    for program in bugcrowd_programs:
        for asset in program['targets']['in_scope']:
            if domain in asset['target'] and asset['type'] in ['website', 'api']:
                return ((program['max_payout'] > 0), program['url'])
    
    return (False, None)


def fetch_wildcard_domains():
    unfiltered_list = requests.get("https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/wildcards.txt").content.decode(encoding="utf-8").splitlines()
    unfiltered_list = [domain[2:] for domain in unfiltered_list if domain.startswith("*.") and domain.count("*") == 1]

    hackerone_programs = json.loads(requests.get("https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json").content.decode(encoding="utf-8"))
    intigriti_programs = json.loads(requests.get("https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/intigriti_data.json").content.decode(encoding="utf-8"))
    bugcrowd_programs = json.loads(requests.get("https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/bugcrowd_data.json").content.decode(encoding="utf-8"))

    domain_info = [domain_program_has_bounties(domain, hackerone_programs, intigriti_programs, bugcrowd_programs) for domain in unfiltered_list]
    
    final_list = [d for d, info in zip(unfiltered_list, domain_info) if info[0]]
    url_list = [info[1] for info in domain_info if info[0]]

    return final_list, url_list

def fetch_new_domains(old_domain_list):
    unfiltered_list = requests.get("https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/domains.txt").content.decode(encoding="utf-8").splitlines()
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

def find_subdomains(wildcard_domain, max_subdomains=0, max_time=15):
    subprocess.run(["subfinder", "-d", wildcard_domain, "-max-time", str(max_time), "-o", "subfinder-output.txt"], stdout=subprocess.DEVNULL)

    subdomain_list = []

    try:
        with open("subfinder-output.txt") as file:
            subdomain_list = file.readlines()
            subdomain_list = [s.strip() for s in subdomain_list]
    except:
        return []

    if max_subdomains == 0:
        return subdomain_list
    else:
        return subdomain_list[:max_subdomains]

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

        wildcard_domain_list, _ = fetch_wildcard_domains()

        for domain in wildcard_domain_list:

            for _ in range(5):
                subs = find_subdomains(domain)
                if len(subs) > 0:
                    break
            
            if len(subs) == 0:
                continue

            submit_to_db(mongo_subdomain_collection, subs)

if __name__ == "__main__":
    print("subdomain-automation started")
    try:
        main()
    except Exception as e:
        print("subdomain-automation triggered an exception: {}".format(e))