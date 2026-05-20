import requests
import json
import pandas as pd

SCIMAGO_CSV = 'scimagojr_df.csv'
ROWS = 10  # <--- ADDED CONSTANT


###############################################################################
# CrossRef function to fetch page ranges
###############################################################################
def get_crossref_pages(doi):
    """
    Given a DOI, query the CrossRef API to return the number of pages.
    - If CrossRef does not have page info or an error occurs, return None.
    - If pages are returned as "123-126", we return 4.
    """
    url = f'https://api.crossref.org/works/{doi}'
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()

        page_str = data['message'].get('page')
        if page_str:
            if '-' in page_str:
                start, end = page_str.split('-', 1)
                start_num = ''.join(ch for ch in start if ch.isdigit())
                end_num = ''.join(ch for ch in end if ch.isdigit())
                if start_num.isdigit() and end_num.isdigit():
                    pg_count = int(end_num) - int(start_num) + 1
                    return pg_count if pg_count > 0 else None
                else:
                    return None
            else:
                # Single page or unexpected format
                return 1
        return None
    except Exception:
        return None


###############################################################################
# CrossRef retrieval with pretty-printing
###############################################################################
def get_crossref_works_for_year(year, query='cancer', rows=10, debug=False):
    """
    Fetch CrossRef works for a given year and query. We filter on:
        from-pub-date:YYYY and until-pub-date:YYYY
    We'll retrieve up to `rows` items. If `debug=True`, we pretty-print
    the returned JSON so you can see exactly what data is included.
    """
    base_url = "https://api.crossref.org/works"
    filter_str = f"from-pub-date:{year},until-pub-date:{year}"
    params = {
        'query': query,
        'filter': filter_str,
        'rows': rows,
    }
    try:
        r = requests.get(base_url, params=params)
        r.raise_for_status()
        data = r.json()

        # Debug: pretty-print the entire JSON response
        if debug:
            print(f"\n=== CrossRef raw JSON for year={year} ===")
            print(json.dumps(data, indent=2))

        items = data['message'].get('items', [])
        return items
    except Exception as e:
        print(f"Error fetching CrossRef data for year={year}: {e}")
        return []


def get_all_crossref_works(year_start=2010, year_end=2024, query='cancer', rows=10, debug=False):
    """
    Collect CrossRef records for the specified year range and query.
    Returns a list of raw item dictionaries from CrossRef.
    """
    all_items = []
    for year in range(year_start, year_end + 1):
        items_for_year = get_crossref_works_for_year(year, query=query, rows=rows, debug=debug)
        all_items.extend(items_for_year)
    return all_items


###############################################################################
# Parsing CrossRef Articles + Authors
###############################################################################
def parse_crossref_record(item):
    """
    Given a single CrossRef record (JSON), parse out:
      - primary_data dict:
          ISSN
          Journal (container-title)
          Article Title (title)
          Language
          Year
          Month
          Day
          Number of Pages
          DOI
          Number of Authors
      - author_data_list
          list of dicts with ORCID, Last Name, First Name, Affiliation
    Return (primary_data, author_data_list).
    """

    # Initialize with empty or default values
    primary_data = {
        'ISSN': '',
        'Journal': '',
        'Article Title': '',
        'Language': '',
        'Year': '',
        'Month': '',
        'Day': '',
        'Number of Pages': '',
        'DOI': '',
        'Number of Authors': '',
    }

    # 1) DOI
    doi = item.get('DOI', '')
    primary_data['DOI'] = doi

    # 2) ISSN (usually a list)
    issn_list = item.get('ISSN', [])
    if issn_list and isinstance(issn_list, list):
        primary_data['ISSN'] = issn_list[0]  # just take the first if multiple

    # 3) Journal name ("container-title" usually a list)
    container_title = item.get('container-title', [])
    if container_title and isinstance(container_title, list):
        primary_data['Journal'] = container_title[0].replace(',', '')

    # 4) Article title ("title" is usually a list)
    titles = item.get('title', [])
    if titles and isinstance(titles, list):
        primary_data['Article Title'] = titles[0].replace(',', '')

    # 5) Language
    language = item.get('language', '')
    primary_data['Language'] = language

    # 6) Publication date (try published-print, published-online, or created)
    date_fields = ['published-print', 'published-online', 'created']
    found_date = None
    for df in date_fields:
        if df in item and 'date-parts' in item[df] and item[df]['date-parts']:
            found_date = item[df]['date-parts'][0]  # e.g. [2020, 3, 15]
            break

    if found_date:
        if len(found_date) > 0:
            primary_data['Year'] = str(found_date[0])
        if len(found_date) > 1:
            primary_data['Month'] = str(found_date[1])
        if len(found_date) > 2:
            primary_data['Day'] = str(found_date[2])

    # 7) Number of Pages
    pg_count = get_crossref_pages(doi)
    if pg_count:
        primary_data['Number of Pages'] = str(pg_count)

    # 8) Authors
    authors = item.get('author', [])
    author_data_list = []
    for auth in authors:
        author_dict = {
            'ORCID': 'NONE',
            'Last Name': 'NONE',
            'First Name': 'NONE',
            'Affiliation': 'NONE'
        }
        # ORCID
        orcid = auth.get('ORCID', '')
        if orcid:
            author_dict['ORCID'] = orcid.strip()

        # Last Name
        family_name = auth.get('family', '')
        if family_name:
            author_dict['Last Name'] = family_name.strip().replace(',', '')

        # First Name
        given_name = auth.get('given', '')
        if given_name:
            author_dict['First Name'] = given_name.strip().replace(',', '')

        # Affiliation (could be multiple)
        aff_list = auth.get('affiliation', [])
        if aff_list and isinstance(aff_list, list):
            aff_names = [a.get('name', '') for a in aff_list if a.get('name')]
            joined_aff = '; '.join([a.replace(',', '') for a in aff_names if a])
            if joined_aff:
                author_dict['Affiliation'] = joined_aff

        author_data_list.append(author_dict)

    primary_data['Number of Authors'] = str(len(author_data_list))

    return primary_data, author_data_list


###############################################################################
# Load Scimago data (same as before)
###############################################################################
def load_scimago_data(csv_path):
    df = pd.read_csv(csv_path, encoding='utf-8', dtype=str).fillna('')
    df.rename(columns={'Issn': 'ISSN'}, inplace=True)

    needed_cols = [
        'ISSN', 'Rank', 'Title', 'SJR', 'H index', 'Country', 'Region',
        'Coverage', 'Categories', 'Areas'
    ]
    for col in needed_cols:
        if col not in df.columns:
            df[col] = ''

    for col in ['SJR', 'Coverage', 'Categories', 'Areas']:
        df[col] = df[col].astype(str).apply(lambda x: x.replace(',', ';'))

    df['Coverage'] = df['Coverage'].apply(lambda x: x.replace(';', '-'))
    df['ISSN'] = df['ISSN'].str.strip()
    return df


###############################################################################
# Match journals to scimago
###############################################################################
def build_journals_df(primary_df, scimago_df):
    primary_df['ISSN'] = primary_df['ISSN'].str.replace('-', '', regex=False).str.strip()
    unique_issns = primary_df['ISSN'].dropna().unique()
    scimago_rows = scimago_df.to_dict('records')

    # Build a set of ISSNs in each scimago row
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
        for row in scimago_rows:
            if issn in row['parsed_issn_set']:
                if issn not in found_issns:
                    found_issns.add(issn)
                    matched_journals.append({
                        'ISSN': issn,
                        'Rank': row.get('Rank', ''),
                        'Title': row.get('Title', ''),
                        'SJR': row.get('SJR', ''),
                        'H index': row.get('H index', ''),
                        'Country': row.get('Country', ''),
                        'Region': row.get('Region', ''),
                        'Coverage': row.get('Coverage', ''),
                        'Categories': row.get('Categories', ''),
                        'Areas': row.get('Areas', ''),
                    })
                break

    journals_df = pd.DataFrame(matched_journals)
    return journals_df


###############################################################################
# Main function
###############################################################################
def get_documents():
    """
    1) Fetch CrossRef records for years 2010–2024 (query='cancer'), up to ROWS per year.
    2) Parse them into primary_df and author_df.
    3) Load scimago data, build journals_df.
    4) Clean/sort data, then write CSVs:
       - primary_df.csv (NO PMID, NO PMC columns)
       - author_df.csv
       - journals_df.csv
    """

    # A. Get CrossRef items (with debug printing for the first year)
    crossref_items = get_all_crossref_works(2010, 2024, query='cancer', rows=ROWS, debug=True)
    print(f"Found {len(crossref_items)} CrossRef items in total...")

    # B. Build primary_df + author_df
    primary_records = []
    author_records = []
    for item in crossref_items:
        primary_data, author_data_list = parse_crossref_record(item)
        if primary_data:
            primary_records.append(primary_data)
        if author_data_list:
            author_records.extend(author_data_list)

    primary_df = pd.DataFrame(primary_records)
    author_df = pd.DataFrame(author_records)

    # Convert Year to numeric, drop rows with no valid year
    primary_df['Year'] = pd.to_numeric(primary_df['Year'], errors='coerce')
    primary_df.dropna(subset=['Year'], inplace=True)

    # Remove leading zeros from Month & Day (e.g., "07" -> "7")
    def strip_leading_zeros(val):
        if pd.notnull(val) and str(val).isdigit():
            return str(int(val))
        return val

    primary_df['Month'] = primary_df['Month'].apply(strip_leading_zeros)
    primary_df['Day'] = primary_df['Day'].apply(strip_leading_zeros)

    # Drop duplicates if the same DOI appears multiple times
    primary_df.drop_duplicates(subset=['DOI'], inplace=True)

    # Sort by Year ascending
    primary_df.sort_values(by='Year', inplace=True)

    # C. Load scimago data
    scimago_df = load_scimago_data(SCIMAGO_CSV)

    # D. Build journals_df
    journals_df = build_journals_df(primary_df, scimago_df)

    # Clean up SJR: replace semicolons with decimal points => "0.774"
    journals_df['SJR'] = journals_df['SJR'].str.replace(';', '.', regex=False)
    journals_df['SJR'] = pd.to_numeric(journals_df['SJR'], errors='coerce')
    journals_df.sort_values(by='SJR', ascending=False, inplace=True)

    # E. Write out CSVs
    primary_df.to_csv('primary_df.csv', index=False, encoding='utf-8')
    author_df.to_csv('author_df.csv', index=False, encoding='utf-8')
    journals_df.to_csv('journals_df.csv', index=False, encoding='utf-8')

    print("Successfully wrote primary_df.csv, author_df.csv, and journals_df.csv.")


if __name__ == '__main__':
    get_documents()
