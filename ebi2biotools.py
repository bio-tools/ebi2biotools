# coding: utf-8
import json
import logging
import unicodedata
import glob
import argparse

import requests
import pandas as pd

EBI_COLLECTION = "EBI Tools"
EMBOSS_EBI_COLLECTION = "EMBOSS at EBI Tools"
EBI_CREDITS = [
    {"name": "Web Production", "typeEntity": "Person", "typeRole": ["Developer"]},
    {"name": "EMBL-EBI", "typeEntity": "Institute", "typeRole": ["Provider"]},
    {
        "typeEntity": "Person",
        "typeRole": ["Primary contact"],
        "url": "http://www.ebi.ac.uk/support/",
    },
    {
        "email": "es-request@ebi.ac.uk",
        "name": "Web Production",
        "typeEntity": "Person",
        "typeRole": ["Primary contact"],
    },
]
EMBOSS_CREDITS = [{"name": "EMBOSS", "typeEntity": "Person", "typeRole": ["Developer"]}]
EBI_DOCUMENTATIONS = [
    {"type": ["Terms of use"], "url": "http://www.ebi.ac.uk/about/terms-of-use"}
]
EBI_LINKS = [{"type": ["Helpdesk"], "url": "http://www.ebi.ac.uk/support/"}]
EBI_OS = ["Linux", "Windows", "Mac"]
EBI_OWNER = "EMBL_EBI"

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

r = requests.get("https://www.ebi.ac.uk/sites/ebi.ac.uk/files/data/resource.json")

BIOTOOLS_CONTENTS = []
BIOTOOLS_BY_HOMEPAGE = {}

def cache_biotools_contents():
    for f in glob.glob("../content/data/*/*.biotools.json"):
        entry = json.load(open(f))
        BIOTOOLS_CONTENTS.append(entry)
        BIOTOOLS_BY_HOMEPAGE[entry["homepage"]] = entry


def norm_str(text):
    text = text.replace("\n", " ")
    text = text.replace("\u2019", " ")
    text = " ".join(text.split())
    return unicodedata.normalize("NFKD", text.strip())


def process(args):
    cache_biotools_contents()
    name_filter = args.service
    biotools_entries = []
    ebi_entries = [e["node"] for e in r.json()["nodes"]]
    for ebi_entry in [
        e["node"]
        for e in r.json()["nodes"]
        if name_filter is None or e["node"]["Title"] == name_filter
    ]:
        biotools_entry = {}
        biotools_entry["credits"] = EBI_CREDITS.copy()
        biotools_entry["collectionID"] = [EBI_COLLECTION]
        if ebi_entry["Title"].startswith("EMBOSS "):
            ebi_entry["Title"] = ebi_entry["Title"][7:]
            biotools_entry["credits"].append(EMBOSS_CREDITS)
            biotools_entry["collectionID"].append(EMBOSS_EBI_COLLECTION)
        tool_id = f"{ebi_entry['Title'].lower().replace(' ', '-')}_ebi"
        tool_name = f"{ebi_entry['Title']} (EBI)"
        biotools_entry["name"] = tool_name
        biotools_entry["biotoolsID"] = tool_id
        biotools_entry["biotoolsCURIE"] = f"biotools:{tool_id}"
        biotools_entry["description"] = norm_str(ebi_entry["Description"])
        biotools_entry["documentation"] = EBI_DOCUMENTATIONS.copy()
        # TODO tool documentation
        biotools_entry["function"] = []
        edam_operations = [
            {"url": function[5:]}
            for function in ebi_entry["Functions"].split(", ")
            if function.startswith("edam:")
        ]
        # TODO function inputs and outputs
        biotools_entry["function"] = {"operation": edam_operations}
        biotools_entry["homepage"] = ebi_entry["URL"]
        biotools_entry["links"] = EBI_LINKS.copy()
        biotools_entry["operatingSystem"] = EBI_OS.copy()
        biotools_entry["owner"] = EBI_OWNER
        #print(json.dumps(biotools_entry, indent=4, sort_keys=True))
        match = lookup_in_biotools(biotools_entry)
        if match:
            biotools_entry["biotoolsID_official"] = match["biotoolsID"]
            biotools_entry["maturity"] = match.get("maturity", None)
            biotools_entry["biotoolsID_collections"] = match.get("collectionID",[])
            logging.info(f"{biotools_entry['name']}, {biotools_entry['homepage']}, ->, {match.get('biotoolsID','')}, {match.get('homepage','')}, {str(match.get('collectionID',''))}")
        else:
            biotools_entry["biotoolsID_official"] = None
            biotools_entry["maturity"] = None
            biotools_entry["biotoolsID_collections"] = []
            logging.info(f"{biotools_entry['name']}, {biotools_entry['homepage']}, -> NO MATCH")
        biotools_entries.append(biotools_entry)
    kept_keys = ["biotoolsID", "homepage", "biotoolsID_official", "biotoolsID_collections", "maturity"]
    df_mapped = pd.DataFrame([{ key: bt_entry[key] for key in kept_keys} for bt_entry in biotools_entries])
    mapped_ids = [bt["biotoolsID_official"] for bt in biotools_entries if bt["biotoolsID_official"]!=None]
    df_nonmapped = pd.DataFrame([("", entry.get("homepage",None), entry["biotoolsID"], entry.get("collectionID",[]), entry.get("maturity", None)) for entry in BIOTOOLS_CONTENTS if EBI_COLLECTION in entry.get("collectionID",[]) and entry["biotoolsID"] not in mapped_ids])
    df_nonmapped.columns = kept_keys
    if args.summary_file:
        pd.concat([df_mapped, df_nonmapped]).to_excel(args.summary_file, sheet_name="Sheet1", index=False)
    logging.info(f"EBI tools:                  {len(biotools_entries):>5}")
    logging.info(f"Bio.tools:                  {len(BIOTOOLS_CONTENTS):>5}")
    logging.info(f"Matched tools:              {len([entry for entry in biotools_entries if 'biotoolsID_official' in entry.keys() and entry['biotoolsID_official']!=None]):>5}")
    logging.info(f"Matched tools with col:     {len([entry for entry in biotools_entries if 'EBI Tools' in entry.get('biotoolsID_collections',[])]):>5}")
    logging.info(f"Non-Matched tools with col: {len(df_nonmapped):>5}")

def lookup_in_biotools(query_entry):
    if query_entry["homepage"] in BIOTOOLS_BY_HOMEPAGE.keys():
        return BIOTOOLS_BY_HOMEPAGE[query_entry["homepage"]]
    return None

def main():
    parser = argparse.ArgumentParser(prog="ebi2biotools")
    parser.set_defaults(func=process)
    parser.add_argument(
        "--service",
        required=False,
        default=None,
        help="process only one service with the name provided here"
    )
    parser.add_argument(
        "--summary-file",
        required=False,
        default=None,
        help="File to summarize statistics obtained from the mapping"
    )
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

