import requests
import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('PUBMED_API_KEY')
BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
SCIMAGO_CSV = 'scimagojr_df.csv'


###############################################################################
# CrossRef function to fetch page ranges
###############################################################################

def get_crossref_pages(doi):
    """
    Given a DOI, query the CrossRef API to return the number of pages.
    - If CrossRef does not have page info or an error occurs, return None.
    - If pages are returned as "123-126", we return "4".
    """
    url = f'https://api.crossref.org/works/{doi}'
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()

        # CrossRef returns the page range (if available) in data['message']['page']
        page_str = data['message'].get('page')
        if page_str:
            if '-' in page_str:
                # Sometimes pages can look like "e123-e127" or "S10-S15"
                # We'll parse out digits only
                start, end = page_str.split('-')
                start_num = ''.join(ch for ch in start if ch.isdigit())
                end_num   = ''.join(ch for ch in end   if ch.isdigit())
                if start_num.isdigit() and end_num.isdigit():
                    pg_count = int(end_num) - int(start_num) + 1
                    return pg_count if pg_count > 0 else None
                else:
                    return None
            else:
                # Single page or unexpected format
                return 1
        return None
except requests.exceptions.RequestException:
def get_paper_ids_for_year(year, query='chemistry', retmax=1000):
    """
    Fetch a list of PubMed IDs (PMIDs) for a given year and query.
    By default, returns up to retmax=100 PMIDs.
    """
    url = (
        f'{BASE_URL}esearch.fcgi'
        f'?db=pubmed'
        f'&term={query}+AND+{year}[pdat]'
        f'&api_key={API_KEY}'
        f'&retmax={retmax}'
    )
    resp = requests.get(url)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    id_list = []
    for child in root.findall('.//IdList/Id'):
        if child.text:
            id_list.append(child.text.strip())
    return id_list


def get_all_pmids(year_start=2010, year_end=2024, query='cancer'):
    """
    Collect PMIDs for the specified year range and query.
    """
    pmid_set = set()
    for year in range(year_start, year_end + 1):
        pmid_set.update(get_paper_ids_for_year(year, query=query))
    return list(pmid_set)


###############################################################################
# Parsing PubMed Articles + Authors (with pages)
###############################################################################

def parse_pubmed_article_and_authors(xml_data, pmid):
    """
    Parse a single PubMed article, returning:
      - primary_data dict (article-level info, including Number_of_Pages, DOI, and PMC ID)
      - author_data_list (list of dicts, one per author)

    Return (None, None) if we skip the record entirely.
    """
    root = ET.fromstring(xml_data)

    # -- Article-level data --
    primary_data = {
        'PMID': pmid,
        'ISSN': '',
        'Journal': '',
        'Article Title': '',
        'Language': '',
        'Year': '',
        'Month': '',
        'Day': '',
        'Number of Pages': '',
        'DOI': '',  # Add DOI field
        'PMC': '',  # Add PMC field
        'Number of Authors': '',  # New column
    }

    # ISSN
    issn_elem = root.find('.//Article/Journal/ISSN')
    if issn_elem is not None and issn_elem.text:
        primary_data['ISSN'] = issn_elem.text.strip()

    # Journal Title
    jtitle_elem = root.find('.//Article/Journal/Title')
    if jtitle_elem is not None and jtitle_elem.text:
        primary_data['Journal'] = jtitle_elem.text.strip().replace(',', '')

    # Article Title
    atitle_elem = root.find('.//Article/ArticleTitle')
    if atitle_elem is not None and atitle_elem.text:
        primary_data['Article Title'] = atitle_elem.text.strip().replace(',', '')

    # Language
    lang_elem = root.find('.//Article/Language')
    if lang_elem is not None and lang_elem.text:
        primary_data['Language'] = lang_elem.text.strip()

    # Date
    date_elem = root.find('.//Article/ArticleDate')
    if date_elem is not None:
        year = date_elem.find('Year')
        month = date_elem.find('Month')
        day = date_elem.find('Day')
        if year is not None and year.text:
            primary_data['Year'] = year.text.strip()
        if month is not None and month.text:
            primary_data['Month'] = month.text.strip()
        if day is not None and day.text:
            primary_data['Day'] = day.text.strip()

    # -- Attempt to parse page ranges from PubMed <Pagination><MedlinePgn> --
    pages_elem = root.find('.//Article/Pagination/MedlinePgn')
    numeric_pages = None

    if pages_elem is not None and pages_elem.text:
        pages_str = pages_elem.text.strip()
        if '-' in pages_str:
            try:
                start, end = pages_str.split('-')
                start_num = ''.join(ch for ch in start if ch.isdigit())
                end_num   = ''.join(ch for ch in end   if ch.isdigit())
                if start_num.isdigit() and end_num.isdigit():
                    numeric_pages = int(end_num) - int(start_num) + 1
                    if numeric_pages < 1 or numeric_pages > 500:
                        numeric_pages = None
            except:
                numeric_pages = None
        else:
            # Single page
            numeric_pages = 1

    if numeric_pages and numeric_pages > 0 and numeric_pages < 501:
        primary_data['Number of Pages'] = str(numeric_pages)

    # -- Extract DOI and PMC IDs --
    # DOI
    doi_elem = root.find('.//ArticleIdList/ArticleId[@IdType="doi"]')  # Corrected XPath
    if doi_elem is not None and doi_elem.text:
        primary_data['DOI'] = doi_elem.text.strip()

    # PMC
    pmc_elem = root.find('.//ArticleIdList/ArticleId[@IdType="pmc"]')  # Corrected XPath
    if pmc_elem is not None and pmc_elem.text:
        primary_data['PMC'] = pmc_elem.text.strip()

    # -- Author-level data --
    author_data_list = []
    author_count = 0
    author_nodes = root.findall('.//AuthorList/Author')
    for auth in author_nodes:
        author_dict = {
            'ORCID': 'NONE',
            'Last Name': 'NONE',
            'First Name': 'NONE',
            'Affiliation': 'NONE'
        }

        # ORCID
        orcid_elem = auth.find('Identifier')
        if orcid_elem is not None and orcid_elem.text:
            author_dict['ORCID'] = orcid_elem.text.strip()

        # LastName
        ln_elem = auth.find('LastName')
        if ln_elem is not None and ln_elem.text:
            author_dict['Last Name'] = ln_elem.text.strip().replace(',', '')

        # ForeName
        fn_elem = auth.find('ForeName')
        if fn_elem is not None and fn_elem.text:
            author_dict['First Name'] = fn_elem.text.strip().replace(',', '')

        # Affiliation
        aff_elem = auth.find('.//Affiliation')
        if aff_elem is not None and aff_elem.text:
            author_dict['Affiliation'] = aff_elem.text.strip().replace(',', '')

        author_count += 1

        author_data_list.append(author_dict)

    primary_data['Number of Authors'] = str(author_count)

    return primary_data, author_data_list


###############################################################################
# Load Scimago data (no exploding), coverage fix, etc.
###############################################################################

def load_scimago_data(csv_path):
    """
    Read scimagojr_df.csv as-is, keep any row that might have multiple ISSNs
    in one cell (e.g. "1542-4863, 0007-9235"). We'll do matching row-by-row.
    """
    df = pd.read_csv(csv_path, encoding='utf-8', dtype=str).fillna('')

    # Adjust columns if necessary
    df.rename(columns={'Issn': 'ISSN'}, inplace=True)

    # Ensure these columns exist
    needed_cols = [
        'ISSN','Rank','Title','SJR','H index','Country','Region',
        'Coverage','Categories','Areas'
    ]
    for col in needed_cols:
        if col not in df.columns:
            df[col] = ''

    # Replace any commas in these fields with semicolons to avoid CSV issues
    for col in ['SJR','Coverage','Categories','Areas']:
        df[col] = df[col].astype(str).apply(lambda x: x.replace(',', ';'))

    # Specifically fix Coverage: replace semicolon with a dash
    df['Coverage'] = df['Coverage'].apply(lambda x: x.replace(';', '-'))

    # We'll keep the ISSN column as is for matching row-by-row, but do
    # a small strip of extra spaces:
    df['ISSN'] = df['ISSN'].str.strip()

    return df


###############################################################################
# Direct row-by-row matching for journals
###############################################################################

def build_journals_df(primary_df, scimago_df):
    """
    We have a list of unique ISSNs from primary_df. For each one, we scan
    scimago_df row by row to see if that ISSN is present (after cleaning out
    hyphens/spaces) in the scimago row's ISSN field (which may contain multiple
    ISSNs separated by commas).
    """

    # Clean hyphens in primary_df ISSN
    primary_df['ISSN'] = primary_df['ISSN'].str.replace('-', '', regex=False).str.strip()

    # Gather unique ISSNs from primary_df
    unique_issns = primary_df['ISSN'].dropna().unique()

    # Convert scimago DataFrame to list of dicts for row-by-row scanning
    scimago_rows = scimago_df.to_dict('records')
    # For quick use, let's add a 'parsed_issn_set' field with hyphens removed
    for row in scimago_rows:
        row_issn_str = row['ISSN'].replace(' ', '')
        splitted = row_issn_str.split(',')
        splitted_cleaned = [sissn.replace('-', '').strip() for sissn in splitted if sissn]
        row['parsed_issn_set'] = set(splitted_cleaned)

    matched_journals = []
    found_issns = set()

    for issn in unique_issns:
        if not issn:
            continue
        # Search scimago row by row
        for row in scimago_rows:
            if issn in row['parsed_issn_set']:
                # Found a match, check if we've used it
                if issn not in found_issns:
                    found_issns.add(issn)
                    matched_journals.append({
                        'ISSN': issn,
                        'Rank': row.get('Rank',''),
                        'Title': row.get('Title',''),
                        'SJR': row.get('SJR',''),
                        'H index': row.get('H index',''),
                        'Country': row.get('Country',''),
                        'Region': row.get('Region',''),
                        'Coverage': row.get('Coverage',''),
                        'Categories': row.get('Categories',''),
                        'Areas': row.get('Areas',''),
                    })
                break

    journals_df = pd.DataFrame(matched_journals)
    return journals_df


###############################################################################
# Main function
###############################################################################

def get_documents():
    """
    1) Fetch PMIDs for 2010–2024, parse primary + author data (including CrossRef pages).
    2) Load scimago data.
    3) Build journals_df by direct row-by-row check.
    4) Clean data (SJR decimal, remove leading zero from Month/Day, sorting).
    5) Write out CSVs: primary_df, author_df, journals_df.
    """

    # -- A. Get PMIDs --
    pmid_list = get_all_pmids(2010, 2024, query='cancer')
    print(f"Found {len(pmid_list)} PMIDs...")

    # -- B. Build primary_df + author_df --
    primary_records = []
    author_records = []

    for pmid in pmid_list:
        url = f'{BASE_URL}efetch.fcgi?db=pubmed&id={pmid}&api_key={API_KEY}&retmode=xml'
        resp = requests.get(url)
        resp.raise_for_status()

        # Pretty print XML response
        # xml_pretty = xml.dom.minidom.parseString(resp.content)  # Parse the raw XML
        # print(xml_pretty.toprettyxml(indent="  "))  # Print with indentation

        primary_data, author_data_list = parse_pubmed_article_and_authors(resp.content, pmid)
        if primary_data:
            primary_records.append(primary_data)
        if author_data_list:
            author_records.extend(author_data_list)

    primary_df = pd.DataFrame(primary_records)
    author_df = pd.DataFrame(author_records)

    # Clean numeric year
    primary_df['Year'] = pd.to_numeric(primary_df['Year'], errors='coerce')
    primary_df.dropna(subset=['Year'], inplace=True)
    primary_df.drop_duplicates(subset=['PMID'], inplace=True)

    # Remove leading zeros from Month & Day (e.g. "07" -> "7")
    primary_df['Month'] = primary_df['Month'].apply(lambda x: str(int(x)) if pd.notnull(x) and str(x).isdigit() else x)
    primary_df['Day'] = primary_df['Day'].apply(lambda x: str(int(x)) if pd.notnull(x) and str(x).isdigit() else x)

    # Sort primary_df by Year ascending
    primary_df.sort_values(by='Year', inplace=True)

    # -- C. Load scimago data
    scimago_df = load_scimago_data(SCIMAGO_CSV)

    # -- D. Build journals_df
    journals_df = build_journals_df(primary_df, scimago_df)

    # Clean up SJR: replace semicolons with decimal points => "0.774"
    journals_df['SJR'] = journals_df['SJR'].str.replace(';', '.', regex=False)
    # Attempt to convert to float
    journals_df['SJR'] = pd.to_numeric(journals_df['SJR'], errors='coerce')

    # Sort journals_df by SJR descending
    journals_df.sort_values(by='SJR', ascending=False, inplace=True)

    # -- E. Write out CSVs
    primary_df.to_csv('primary_df.csv', index=False, encoding='utf-8')
    author_df.to_csv('author_df.csv', index=False, encoding='utf-8')
    journals_df.to_csv('journals_df.csv', index=False, encoding='utf-8')

    print("Successfully wrote primary_df.csv, author_df.csv, and journals_df.csv.")


if __name__ == '__main__':
    get_documents()
