# coding: utf-8

import json
import unicodedata

import requests

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

r = requests.get("https://www.ebi.ac.uk/sites/ebi.ac.uk/files/data/resource.json")


def norm_str(text):
    text = text.replace("\n", " ")
    text = text.replace("\u2019", " ")
    text = " ".join(text.split())
    return unicodedata.normalize("NFKD", text.strip())


def main(name_filter):
    biotools_entries = []
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
        print(json.dumps(biotools_entry, indent=4, sort_keys=True))
        biotools_entries.append(biotools_entry)
    print(f"Processed {len(biotools_entries)} EBI tools")


main("EMBOSS needle")
