import pandas as pd
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from PyPDF2 import PdfReader
import os
import time

def get_pdf_page_count(pdf_url, save_path="temp.pdf"):
    """Download the PDF and extract the number of pages using requests."""
    try:
        response = requests.get(pdf_url, timeout=10)
        response.raise_for_status()  # Ensure the request was successful
        with open(save_path, "wb") as f:
            f.write(response.content)
        reader = PdfReader(save_path)
        page_count = len(reader.pages)
        return page_count
    except Exception as e:
        raise RuntimeError(f"Error reading PDF: {e}")
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)

def process_rows(driver, df, base_domain, start_idx, end_idx):
    """Process a range of rows in the dataset."""
    cookies_handled = False
    iteration_count = 0

    for idx in range(start_idx, end_idx):
        if pd.isna(df.loc[idx, "pages"]):
            row = df.loc[idx]
            doi_url = row["doi"]

            driver.get(doi_url)

            # Handle cookies on the first iteration only
            if not cookies_handled:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonAccept"))
                    ).click()
                    cookies_handled = True
                except Exception:
                    pass  # No cookie popup

            # Click the download dropdown
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-dropdown^="drop-download"]'))
                ).click()
            except Exception as e:
                print(f"Error clicking download dropdown for row {idx + 1}: {e}")
                continue

            # Wait for and get the PDF download button
            try:
                download_pdf_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "UD_ArticlePDF"))
                )
                pdf_url = download_pdf_button.get_attribute("href")
                pdf_url = base_domain + pdf_url if not pdf_url.startswith("http") else pdf_url
            except Exception as e:
                print(f"Error locating or interacting with PDF button for row {idx + 1}: {e}")
                continue

            # Extract the page count from the PDF
            try:
                new_page_count = get_pdf_page_count(pdf_url)
                # Update the dataset
                df.loc[idx, "pages"] = new_page_count
                # Log successful update
                iteration_count += 1
                print(f"Successfully updated row {idx + 1}, Page Count = {new_page_count}")
            except RuntimeError as e:
                print(f"Error extracting page count from PDF for row {idx + 1}: {e}")
                continue

            # Delay after each iteration to avoid rate limiting
            time.sleep(2)  # Add a 2-second delay between each request

            # Reset the session after every 100 iterations
            if iteration_count % 100 == 0:
                print("Resetting session after 100 iterations to avoid rate limiting...")
                driver.quit()
                time.sleep(10)  # Give a brief pause before restarting
                return iteration_count  # Return early to restart the session

    return iteration_count

def main():
    # Load the dataset
    file_path = "updated_articles.csv"  # Adjust the file path if needed
    df = pd.read_csv(file_path)

    base_domain = "https://www.mdpi.com"

    total_iterations = 0
    batch_size = 50  # Keep the original batch size

    while df["pages"].isna().any():
        start_idx = df["pages"].isna().idxmax()
        end_idx = start_idx + batch_size

        with SB(uc=True, headless=True) as sb:  # Enable headless mode
            total_iterations += process_rows(sb.driver, df, base_domain, start_idx, end_idx)

        print(f"Completed {total_iterations} iterations. Saving progress...")

        # Save progress after each batch
        df.to_csv("updated_articles.csv", index=False)

    print("Dataset updated and saved as 'updated_articles.csv'.")

if __name__ == "__main__":
    main()
