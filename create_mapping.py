# coding: utf-8
import json
import logging
import unicodedata
import glob
import argparse

import requests
import pandas as pd

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
url = "https://www.ebi.ac.uk/api/v1/resources-all?source=contentdb"
r = requests.get(url)

BIOTOOLS_CONTENTS = []
BIOTOOLS_BY_HOMEPAGE = {}
EBI_COLLECTION = "EBI Tools"


def cache_biotools_contents():
    for f in glob.glob("../content/data/*/*.biotools.json"):
        entry = json.load(open(f))
        entry["homepage"] = entry["homepage"].replace("http://", "https://")
        BIOTOOLS_CONTENTS.append(entry)
        BIOTOOLS_BY_HOMEPAGE[entry["homepage"]] = entry


def norm_str(text):
    text = text.replace("\n", " ")
    text = text.replace("\u2019", " ")
    text = " ".join(text.split())
    return unicodedata.normalize("NFKD", text.strip())


def lookup_in_biotools(query_entry):
    if query_entry["URL"] in BIOTOOLS_BY_HOMEPAGE.keys():
        return BIOTOOLS_BY_HOMEPAGE[query_entry["URL"]]
    return None


def process(args):
    cache_biotools_contents()
    ebi_entries_mapped = []
    ebi_entries = [e["node"] for e in r.json()["nodes"]]
    for ebi_entry in [
        e["node"] for e in r.json()["nodes"] if e["node"]["Domain"] != "Project Website"
    ]:
        ebi_entry["URL"] = ebi_entry["URL"].replace("http://", "https://")
        ebi_entry["Description"] = norm_str(ebi_entry["Description"])
        ebi_entry["Short description"] = norm_str(ebi_entry["Short description"])
        ebi_entry["Logo"] = ebi_entry["Logo"]["src"]
        ebi_entry["Logo-thumbnail"] = ebi_entry["Logo-thumbnail"]["src"]
        del ebi_entry["short_description"]
        match = lookup_in_biotools(ebi_entry)
        if match:
            ebi_entry["bio.tools ID"] = match["biotoolsID"]
            ebi_entry["bio.tools maturity"] = match.get("maturity", None)
            ebi_entry["bio.tools collections"] = match.get("collectionID", [])
        else:
            ebi_entry["bio.tools ID"] = None
            ebi_entry["bio.tools maturity"] = None
            ebi_entry["bio.tools collections"] = None
        ebi_entries_mapped.append(ebi_entry)
    df_mapped = pd.DataFrame(ebi_entries_mapped)

    mapped_ids = [
        bt["bio.tools ID"] for bt in ebi_entries_mapped if bt["bio.tools ID"] != None
    ]
    df_nonmapped = pd.DataFrame(
        [
            {
                "bio.tools ID": entry["biotoolsID"],
                "bio.tools collections": entry.get("collectionID", []),
                "bio.tools maturity": entry.get("maturity", None),
                "Category": None,
                "Description": None,
                "Domain": None,
                "Email": None,
                "Functions": None,
                "Keywords": None,
                "Logo": None,
                "Logo-thumbnail": None,
                "Maintainer": None,
                "Nid": None,
                "Popular": None,
                "Primary contact": None,
                "Short description": None,
                "Short name": None,
                "Title": None,
                "URL": entry["homepage"],
                "Weight": None,
                "data_licence_type": None,
                "maturity": None,
                "resource_api_compliant": None,
                "resource_out_of_ebi_ctrl": None,
                "resource_rest_landing_page": None,
            }
            for entry in BIOTOOLS_CONTENTS
            if EBI_COLLECTION in entry.get("collectionID", [])
            and entry["biotoolsID"] not in mapped_ids
        ]
    )
    logging.info(f"EBI tools:                  {len(ebi_entries):>5}")
    logging.info(f"Bio.tools:                  {len(BIOTOOLS_CONTENTS):>5}")
    logging.info(
        f"Matched tools:              {len([entry for entry in ebi_entries_mapped if 'biotoolsID' in entry.keys() and entry['biotoolsID']!=None]):>5}"
    )
    logging.info(f"Non-Matched tools with col: {len(df_nonmapped):>5}")
    if args.summary_file:
        writer = pd.ExcelWriter(args.summary_file, engine='xlsxwriter')
        df_identified = pd.concat([df_mapped, df_nonmapped])
        df_identified = df_identified[
            [
                "bio.tools ID",
                "bio.tools collections",
                "bio.tools maturity",
                "Nid",
                "Title",
                "URL",
                "Category",
                "Description",
                "Domain",
                "Email",
                "Functions",
                "Keywords",
                "Maintainer",
                "Popular",
                "Primary contact",
                "Short description",
                "Short name",
                "Weight",
                "data_licence_type",
                "maturity",
                "resource_api_compliant",
                "resource_out_of_ebi_ctrl",
                "resource_rest_landing_page",
                "Logo",
                "Logo-thumbnail",
            ]
        ]
        df_identified.to_excel(writer, sheet_name="EBI-bio.tools", index=False)
        workbook  = writer.book
        worksheet = writer.sheets["EBI-bio.tools"]
        research_format = workbook.add_format({'bg_color': '#FFC7CE',
                               'font_color': '#9C0006'})
        # worksheet.conditional_format('I1:I1048576', {'type': 'cell',
        #                                  'criteria': '==',
        #                                  'value': 'Research',
        #                                  'format': research_format})
        worksheet.conditional_format('A1:Z1048576', {'type': 'formula',
                                          'criteria': '=LEFT($I1, 8)="Research"',
                                          'format': research_format})
        writer.save()


def main():
    parser = argparse.ArgumentParser(prog="ebi2biotools")
    parser.set_defaults(func=process)
    parser.add_argument(
        "--service",
        required=False,
        default=None,
        help="process only one service with the name provided here",
    )
    parser.add_argument(
        "--summary-file",
        required=False,
        default=None,
        help="File to summarize statistics obtained from the mapping",
    )
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
