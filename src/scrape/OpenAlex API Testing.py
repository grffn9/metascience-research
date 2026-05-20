import requests
import pandas as pd
from datetime import datetime
import time

# Constants and Configurations
SCIMAGO_CSV = 'C:/Users/griff/OneDrive/Desktop/Research/Data Collection/SCIMAG/scimagojr_df.csv'
ROWS = 10  # Desired number of valid articles per journal per year
MAX_PAGE_LIMIT = 500  # Maximum number of pages to fetch per journal per year to avoid infinite loops
MAILTO_CONTACT = "griffin.munhall@gmail.com"

# List of Journal Sources (Only one active for testing; others are commented out)
JOURNAL_SOURCES = [
    ("CA A Cancer Journal for Clinicians", "s126094547"),
    ("International Journal of Molecular Sciences", "s10623703"),
    ("Journal of Biological Chemistry", "s140251998"),
    ("IEEE Access", "s2485537415"),
]

###############################################################################
# CrossRef Pages Helper
###############################################################################
def get_crossref_pages(doi):
    if not doi:
        return None
    url = f'https://api.crossref.org/works/{doi}'
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        page_str = data['message'].get('page')
        if page_str:
            if '-' in page_str:
                start, end = page_str.split('-', 1)
                start_num = ''.join(filter(str.isdigit, start))
                end_num = ''.join(filter(str.isdigit, end))
                if start_num.isdigit() and end_num.isdigit():
                    pg_count = int(end_num) - int(start_num) + 1
                    if 0 < pg_count <= MAX_PAGE_LIMIT:
                        return pg_count
            else:
                return 1
    except Exception as e:
        print(f"Error fetching CrossRef pages for DOI={doi}: {e}")
    return None

###############################################################################
# Helper Function to Check Publication Status and Additional Filters
###############################################################################
def is_valid_article(work, target_display_name="CA A Cancer Journal for Clinicians"):
    """
    Checks if the article meets the following criteria:
    - Published and accepted in the specified journal.
    - has_fulltext is True.
    - referenced_works_count is greater than 0.
    - Number of Pages is greater than 1.

    Args:
        work (dict): The article JSON object.
        target_display_name (str): The display_name to filter locations.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Check in 'primary_location'
    primary_location = work.get('primary_location')
    if isinstance(primary_location, dict):
        source = primary_location.get('source', {})
        if not isinstance(source, dict):
            source = {}
        display_name = source.get('display_name', "")
        if display_name == target_display_name:
            is_published = primary_location.get('is_published', False)
            is_accepted = primary_location.get('is_accepted', False)
            if is_published and is_accepted:
                # **New Filter 3: Exclude articles with 1 or fewer pages**
                biblio = work.get('biblio', {}) or {}
                first_page = biblio.get('first_page', '')
                last_page = biblio.get('last_page', '')
                page_count = None

                if first_page and last_page:
                    start_num = ''.join(filter(str.isdigit, first_page))
                    end_num = ''.join(filter(str.isdigit, last_page))
                    if start_num.isdigit() and end_num.isdigit():
                        possible_count = int(end_num) - int(start_num) + 1
                        if possible_count <= 1:
                            return False
                        else:
                            page_count = possible_count
                elif work.get('doi', ''):
                    pg_count = get_crossref_pages(work.get('doi'))
                    if pg_count and pg_count <= 1:
                        return False

                # **Existing Filter 1: Exclude articles without full text**
                if not work.get('has_fulltext', False):
                    return False
                # **Existing Filter 2: Exclude articles with zero references**
                if work.get('referenced_works_count', 0) == 0:
                    return False
                return True

    # Check in 'locations' list
    locations = work.get('locations', [])
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        source = loc.get('source', {})
        if not isinstance(source, dict):
            source = {}
        display_name = source.get('display_name', "")
        if display_name == target_display_name:
            is_published = loc.get('is_published', False)
            is_accepted = loc.get('is_accepted', False)
            if is_published and is_accepted:
                # **New Filter 3: Exclude articles with 1 or fewer pages**
                biblio = work.get('biblio', {}) or {}
                first_page = biblio.get('first_page', '')
                last_page = biblio.get('last_page', '')
                page_count = None

                if first_page and last_page:
                    start_num = ''.join(filter(str.isdigit, first_page))
                    end_num = ''.join(filter(str.isdigit, last_page))
                    if start_num.isdigit() and end_num.isdigit():
                        possible_count = int(end_num) - int(start_num) + 1
                        if possible_count <= 1:
                            return False
                        else:
                            page_count = possible_count
                elif work.get('doi', ''):
                    pg_count = get_crossref_pages(work.get('doi'))
                    if pg_count and pg_count <= 1:
                        return False

                # **Existing Filter 1: Exclude articles without full text**
                if not work.get('has_fulltext', False):
                    return False
                # **Existing Filter 2: Exclude articles with zero references**
                if work.get('referenced_works_count', 0) == 0:
                    return False
                return True

    return False

###############################################################################
# Query OpenAlex using the "source.id" approach with Publication Status Filtering
###############################################################################
def get_openalex_articles_by_source(source_id, publication_year, article_type="types/article",
                                    sort_by="cited_by_count:desc", per_page=100000, page=1):
    base_url = "https://api.openalex.org/works"
    query_filter = (
        f"primary_location.source.id:{source_id},"
        f"publication_year:{publication_year},"
        f"type:{article_type}"
    )
    params = {
        "page": page,
        "filter": query_filter,
        "sort": sort_by,
        "per_page": per_page,
        "mailto": MAILTO_CONTACT,
    }
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('results', [])
    except Exception as e:
        print(f"Error fetching data for source={source_id}, year={publication_year}, page={page}: {e}")
        return []

###############################################################################
# Parse a Single Article Record
###############################################################################
def parse_openalex_record(work, journal_name):
    primary_data = {
        'Journal': journal_name,
        'ISSN': '',
        'Article Title': '',
        'Language': '',
        'Year': '',
        'Month': '',
        'Day': '',
        'Number of Pages': '',
        'DOI': '',
        'Number of Authors': '',
    }

    primary_location = work.get('primary_location') or {}
    source_data = primary_location.get('source') or {}

    issns_list = source_data.get('issns') or []
    if not isinstance(issns_list, list):
        issns_list = [issns_list] if issns_list else []

    issn_l = (source_data.get('issn_l') or '').strip()
    if issn_l and issn_l not in issns_list:
        issns_list.append(issn_l)

    issns_str = ':'.join(sorted(set(x.strip() for x in issns_list if x.strip())))
    primary_data['ISSN'] = issns_str

    title = work.get('display_name', '') or ''
    primary_data['Article Title'] = title.replace(',', '')

    lang = work.get('language', '') or primary_location.get('language', '')
    primary_data['Language'] = str(lang)

    pub_year = work.get('publication_year')
    pub_date = work.get('publication_date')
    if pub_year:
        primary_data['Year'] = str(pub_year)
    if pub_date:
        try:
            dt = datetime.strptime(pub_date, "%Y-%m-%d")
            primary_data['Year'] = str(dt.year)
            primary_data['Month'] = str(dt.month)
            primary_data['Day'] = str(dt.day)
        except:
            pass

    doi = work.get('doi', '') or work.get('ids', {}).get('doi', '')
    primary_data['DOI'] = doi

    authorships = work.get('authorships', []) or []
    author_data_list = []
    for auth in authorships:
        auth_author = auth.get('author', {}) or {}
        institutions = auth.get('institutions', []) or []

        author_dict = {
            'Last Name': 'NONE',
            'First Name': 'NONE',
            'ORCID': 'NONE',
            'Affiliation': 'NONE',
            'ISSN': issns_str
        }

        orcid_val = auth_author.get('orcid', '')
        if orcid_val:
            author_dict['ORCID'] = orcid_val

        full_name = (auth_author.get('display_name') or '').strip()
        if full_name:
            parts = full_name.split()
            if len(parts) > 1:
                author_dict['Last Name'] = parts[-1].replace(',', '')
                author_dict['First Name'] = ' '.join(parts[:-1]).replace(',', '')
            else:
                author_dict['Last Name'] = full_name

        aff_list = [inst.get('display_name', '').replace(',', '') for inst in institutions if inst.get('display_name')]
        if aff_list:
            author_dict['Affiliation'] = '; '.join(aff_list)

        author_data_list.append(author_dict)

    primary_data['Number of Authors'] = str(len(author_data_list))

    biblio = work.get('biblio', {}) or {}
    first_page = biblio.get('first_page', '')
    last_page = biblio.get('last_page', '')
    page_count = None

    if first_page and last_page:
        start_num = ''.join(filter(str.isdigit, first_page))
        end_num = ''.join(filter(str.isdigit, last_page))
        if start_num.isdigit() and end_num.isdigit():
            possible_count = int(end_num) - int(start_num) + 1
            if 0 < possible_count <= MAX_PAGE_LIMIT:
                page_count = possible_count

    if page_count is not None:
        primary_data['Number of Pages'] = str(page_count)
    elif doi:
        pg_count = get_crossref_pages(doi)
        if pg_count:
            primary_data['Number of Pages'] = str(pg_count)

    return primary_data, author_data_list

###############################################################################
# Load Scimago Data
###############################################################################
def load_scimago_data(csv_path):
    df = pd.read_csv(csv_path, encoding='utf-8', dtype=str).fillna('')
    df.rename(columns={'Issn': 'ISSN'}, inplace=True)

    needed_cols = ['ISSN', 'Rank', 'Title', 'SJR', 'H index', 'Country', 'Region', 'Coverage', 'Categories', 'Areas']
    for col in needed_cols:
        if col not in df.columns:
            df[col] = ''

    for col in ['Coverage', 'Categories', 'Areas']:
        df[col] = df[col].str.replace(',', ';')
    df['Coverage'] = df['Coverage'].str.replace(';', '-')

    if 'SJR' in df.columns:
        df['SJR'] = df['SJR'].str.replace(',', '.')

    df['ISSN'] = df['ISSN'].str.strip()
    return df

###############################################################################
# Match ISSNs with Scimago
###############################################################################
def build_journals_df(primary_df, scimago_df):
    if primary_df.empty:
        return pd.DataFrame()

    primary_df['ISSN'] = primary_df['ISSN'].str.replace('-', '').str.strip()
    unique_issns = set(issn for val in primary_df['ISSN'].unique() for issn in val.split(':') if issn.strip())

    scimago_rows = scimago_df.to_dict('records')
    for row in scimago_rows:
        row['parsed_issn_set'] = set(
            sissn.replace('-', '').strip() for sissn in row['ISSN'].replace(' ', '').split(',') if sissn
        )

    matched_journals = []
    found_issns = set()

    for issn in unique_issns:
        for row in scimago_rows:
            if issn in row['parsed_issn_set'] and issn not in found_issns:
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

    return pd.DataFrame(matched_journals)

###############################################################################
# Main Function to Gather Documents
###############################################################################
def get_documents():
    all_primary_records = []
    all_author_records = []

    for journal_name, source_id in JOURNAL_SOURCES:
        print(f"\nProcessing journal: {journal_name}, source_id={source_id}")
        for year in range(2015, 2025):
            collected_articles = []
            page = 1
            while len(collected_articles) < ROWS and page <= MAX_PAGE_LIMIT:
                articles = get_openalex_articles_by_source(
                    source_id=source_id,
                    publication_year=year,
                    article_type="types/article",
                    sort_by="cited_by_count:desc",
                    per_page=ROWS,  # Can be increased if needed
                    page=page
                )
                if not articles:
                    break  # No more articles to fetch

                for art in articles:
                    # Check publication status and new filters
                    if is_valid_article(art, target_display_name=journal_name):
                        collected_articles.append(art)
                        if len(collected_articles) == ROWS:
                            break  # Desired number of articles collected

                page += 1  # Move to next page
                time.sleep(1)  # Respect API rate limits

            found_count = len(collected_articles)
            if found_count < ROWS:
                print(f"  WARNING: Year={year}, only {found_count} valid results returned.")
            else:
                print(f"  Year={year} -> got {found_count} valid results.")

            for art in collected_articles:
                primary, authors = parse_openalex_record(art, journal_name)
                all_primary_records.append(primary)
                all_author_records.extend(authors)

    # Create DataFrames
    primary_df = pd.DataFrame(all_primary_records).drop_duplicates(subset=['DOI'])
    author_df = pd.DataFrame(all_author_records)

    if primary_df.empty:
        print("No valid articles were collected. Exiting script to prevent errors.")
        return

    # Convert Year to numeric and sort
    primary_df['Year'] = pd.to_numeric(primary_df['Year'], errors='coerce')
    primary_df.dropna(subset=['Year'], inplace=True)
    primary_df.sort_values(by='Year', inplace=True)

    # Clean up months/days
    for col in ['Month', 'Day']:
        if col in primary_df.columns:
            primary_df[col] = primary_df[col].apply(lambda x: str(int(x)) if isinstance(x, str) and x.isdigit() else x)

    # Build journals_df from Scimago
    scimago_df = load_scimago_data(SCIMAGO_CSV)
    journals_df = build_journals_df(primary_df, scimago_df)

    # Convert SJR to numeric and sort
    if not journals_df.empty and 'SJR' in journals_df.columns:
        journals_df['SJR'] = pd.to_numeric(journals_df['SJR'], errors='coerce')
        journals_df.sort_values(by='SJR', ascending=False, inplace=True)

    # Define output path
    output_path = 'C:/Users/griff/OneDrive/Desktop/Research/Data Collection/Testing/'

    # Save DataFrames to CSV
    primary_df.to_csv(f'{output_path}primary_df.csv', index=False, encoding='utf-8')
    author_df.to_csv(f'{output_path}author_df.csv', index=False, encoding='utf-8')
    journals_df.to_csv(f'{output_path}journals_df.csv', index=False, encoding='utf-8')

    print("\nSuccessfully wrote primary_df.csv, author_df.csv, journals_df.csv.")

if __name__ == '__main__':
    get_documents()
