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
        f"Matched tools:              {len([entry for entry in ebi_entries_mapped if 'bio.tools ID' in entry.keys() and entry['bio.tools ID']!=None]):>5}"
    )
    logging.info(f"Non-Matched tools with col: {len(df_nonmapped):>5}")
    if args.summary_file:
        writer = pd.ExcelWriter(args.summary_file, engine='xlsxwriter')

        workbook  = writer.book

        instructions_sheet = workbook.add_worksheet("Instructions")
        instructions_sheet.set_row(0, 150)
        instructions_sheet.set_column('A:A', 2500)
        instructions_format = workbook.add_format()
        instructions_format.set_text_wrap()
        bold = workbook.add_format({'bold': True})
        text = [bold,
                "Goal of this workbook\n",
                "Link the existing entries of bio.tools entries to the contents database, to make sure we can synchronize the non-extinct EBI services between the EBI Contents DB and bio.tools\n",
                bold,
                "Where do the data of this workbook come from?\n",
                f"The entries in the EBI-bio.tools worksheet were retrieved and merged from bio.tools and contents DB. They are a union of all contents DB entries (sometimes automatically mapped to a bio.tools ID using the URL for the service), and the bio.tools entries identified as EBI because they belonged to the \"{EBI_COLLECTION}\" collection even though no corresponding entry in contents DB was identified.\n",
                bold,
                "What to do with these lines?\n",
                "- if a content DB entry has an bio.tools ID, do not do anything unless you judge it invalid.\n",
                "- if a content DB entry does not have a bio.tools ID, decide or not whether we want to create one, and type requested ID in bold in column A\n",
                "- if a bio.tools entry is not mapped to a content DB entry, suggest an existing content DB Nid in column B or specify other action in column Z"
        ]
        rc = instructions_sheet.write_rich_string("A1", *text, instructions_format)



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
        # add conditional formatting to the worksheet
        worksheet = writer.sheets["EBI-bio.tools"]
        research_format = workbook.add_format({'font_color': '#045D5D'})
        worksheet.conditional_format('A2:Z1048576', {'type': 'formula',
                                          'criteria': '=LEFT($I2, 8)="Research"',
                                          'format': research_format})
        mapped_format = workbook.add_format({'bg_color': '#5cb85c'})
        worksheet.conditional_format('A2:Z1048576', {'type': 'formula',
                                          'criteria': '=AND($A2<>"",$D2<>"")',
                                          'format': mapped_format})
        ebi_unmapped_format = workbook.add_format({'bg_color': '#f0ad4e'})
        worksheet.conditional_format('A2:Z1048576', {'type': 'formula',
                                          'criteria': '=AND($A2="",$D2<>"")',
                                          'format': ebi_unmapped_format})
        biotools_unmapped_format = workbook.add_format({'bg_color': '#5bc0de'})
        worksheet.conditional_format('A2:Z1048576', {'type': 'formula',
                                          'criteria': '=AND($A2<>"",$D2="")',
                                          'format': biotools_unmapped_format})
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
