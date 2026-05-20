from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from bs4.dammit import UnicodeDammit
import csv
import re
import time
import unicodedata

# Constants
BASE_URL = "https://www.mdpi.com/1422-0067"
ARTICLE_CSV_OUTPUT = "ijms_articles_2017_2025.csv"
AUTHOR_CSV_OUTPUT = "ijms_authors_2017_2025.csv"
JOURNAL_NAME = "IJMS"
ISSN = "1422-0067"

# Function to clean text (remove commas, handle Unicode issues, normalize to ASCII)
def clean_text(text):
    if text is None:
        return ""
    clean = unicodedata.normalize("NFKD", UnicodeDammit(text).unicode_markup)
    clean = clean.encode("ascii", "ignore").decode("utf-8")  # Remove non-ASCII characters
    return clean.replace(",", "").strip()

# Function to sanitize issue links (remove duplicate ISSN entries)
def sanitize_link(link):
    return re.sub(r"(/1422-0067)+", "/1422-0067", link)

# Function to extract the issue number from the URL
def extract_issue_number(link):
    match = re.search(r'/1422-0067/\d+/(\d+)$', link)
    return int(match.group(1)) if match else float('inf')

# Function to extract the volume number from the issue URL
def extract_volume_number(link):
    match = re.search(r'/1422-0067/(\d+)/', link)
    return int(match.group(1)) if match else None

# Function to scroll through the page to load all articles
def scroll_through_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        try:
            # Wait up to 10s for the page height to increase
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.body.scrollHeight") > last_height
            )
            last_height = driver.execute_script("return document.body.scrollHeight")
        except:
            # If wait times out, we've likely hit the bottom
            break
    print("Finished scrolling through the page.")

# Setup Chrome WebDriver in headless mode
options = Options()
options.add_argument("--headless")  # Run in headless mode
options.add_argument("--disable-gpu")  # Disable GPU acceleration (optional)
options.add_argument("--start-maximized")  # Simulate full-screen browser
driver_service = Service()  # Provide path to chromedriver if necessary
driver = Chrome(service=driver_service, options=options)

try:
    # Open the main page (Volumes list)
    driver.get(BASE_URL)

    # Accept cookies
    try:
        cookie_accept_button = driver.find_element(By.ID, "CybotCookiebotDialogBodyButtonAccept")
        cookie_accept_button.click()
        print("Accepted cookies.")
    except Exception as e:
        print(f"No cookie dialog found or unable to click accept button: {e}")

    # Parse the main page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Extract links to volumes from Volume 17 (2017) to Volume 25 (2025)
    volume_links = []
    volume_elements = soup.find_all("a", href=re.compile(r"/1422-0067/\d+$"))
    for volume in volume_elements:
        volume_number = int(volume['href'].split('/')[-1])
        if 17 <= volume_number <= 25:  # Limit to Volume 17 through 25
            volume_links.append(BASE_URL + "/" + str(volume_number))
    print(f"Found volumes: {volume_links}")

    # Prepare CSV files for cumulative output
    with open(ARTICLE_CSV_OUTPUT, mode='w', newline='', encoding='utf-8') as article_csvfile, \
         open(AUTHOR_CSV_OUTPUT, mode='w', newline='', encoding='utf-8') as author_csvfile:

        # Set up writers
        article_writer = csv.writer(article_csvfile)
        author_writer = csv.writer(author_csvfile)

        # Write headers
        article_writer.writerow([
            "journal_name",
            "ISSN",
            "title",
            "language",
            "year",
            "month",
            "day",
            "pages",
            "doi",
            "number_of_authors"
        ])
        author_writer.writerow(["Last Name", "First Name", "ISSN"])

        # Initialize a set for unique authors
        unique_authors = set()

        # Process each volume
        for volume_link in volume_links:
            print(f"\nProcessing volume: {volume_link}")
            driver.get(volume_link)
            volume_soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Extract links to issues within the volume
            issue_links = set()  # Use a set to avoid duplicates
            issue_elements = volume_soup.find_all("a", href=re.compile(r"/1422-0067/\d+/\d+$"))
            for issue in issue_elements:
                sanitized_link = sanitize_link(BASE_URL + issue['href'])
                volume_number = extract_volume_number(sanitized_link)
                if volume_number and 17 <= volume_number <= 25:  # Ensure volume is within the valid range
                    issue_links.add(sanitized_link)  # Add sanitized link to the set
            issue_links = sorted(list(issue_links), key=extract_issue_number)  # Sort issues by numeric order
            print(f"  Filtered issues: {issue_links}")

            # Process each issue
            for issue_link in issue_links:
                print(f"    Processing issue: {issue_link}")
                driver.get(issue_link)

                # Scroll through the issue page to load all articles
                scroll_through_page(driver)

                # Parse the loaded issue page
                issue_soup = BeautifulSoup(driver.page_source, 'html.parser')

                # Find article containers
                article_containers = issue_soup.find_all("div", class_="generic-item article-item")
                print(f"      Found {len(article_containers)} articles in this issue.")

                # Track seen DOIs to prevent duplicates
                seen_dois = set()

                # Process each article
                for idx, article in enumerate(article_containers):
                    print(f"      Processing article {idx + 1}...")

                    # Check if the item is an article based on <span class="label articletype">Article</span>
                    article_type_element = article.find("span", class_="label articletype")
                    if not article_type_element or article_type_element.get_text(strip=True) != "Article":
                        print("      Skipping non-article item.")
                        continue

                    # Extract DOI
                    doi_element = article.find("a", href=re.compile(r"^https://doi\.org/"))
                    if doi_element:
                        doi = clean_text(doi_element["href"])
                        if doi in seen_dois:
                            print(f"      Skipping duplicate DOI: {doi}")
                            continue
                        seen_dois.add(doi)
                    else:
                        doi = "N/A"

                    # Extract title
                    title_element = article.find("a", class_="title-link")
                    title = clean_text(title_element.get_text(strip=True)) if title_element else "N/A"

                    # Extract authors
                    authors_element = article.find("div", class_="authors")
                    if authors_element:
                        author_spans = authors_element.find_all("span", class_="inlineblock")
                        authors_list = [clean_text(span.get_text(strip=True)) for span in author_spans]
                        for author in authors_list:
                            parts = author.split(" ")
                            last_name = clean_text(parts[-1])
                            first_name = clean_text(" ".join(parts[:-1]))
                            unique_authors.add((last_name, first_name, ISSN))
                        number_of_authors = len(authors_list)
                    else:
                        number_of_authors = 0

                    # Extract publication date
                    article_text = article.get_text(" ", strip=True)
                    match_date = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', article_text)
                    if match_date:
                        day = clean_text(match_date.group(1))
                        month_str = clean_text(match_date.group(2))
                        year = clean_text(match_date.group(3))
                    else:
                        day, month_str, year = ("N/A", "N/A", "N/A")

                    # Convert month name to number
                    month_map = {
                        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                    }
                    month = month_map.get(month_str[:3], month_str)

                    # Extract number of pages
                    pages_match = re.search(r'(\d+)\s+pages', article_text)
                    pages = clean_text(pages_match.group(1)) if pages_match else "N/A"

                    # Write article data to CSV
                    article_writer.writerow([
                        JOURNAL_NAME,
                        ISSN,
                        title,
                        "English",  # Default language
                        year,
                        month,
                        day,
                        pages,
                        doi,
                        number_of_authors
                    ])

                print(f"      Finished processing issue: {issue_link}")

        # Write unique authors to CSV
        for last_name, first_name, issn in unique_authors:
            author_writer.writerow([last_name, first_name, issn])

    print("Completed processing all volumes and issues.")

finally:
    driver.quit()
