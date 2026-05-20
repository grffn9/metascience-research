# Academic Metascience & Bibliometric Analysis

## Description
This project conducts a comprehensive bibliometric analysis of academic journals, specifically targeting publication trends, demographic representations (gender, ethnicity), and journal metrics (SJR/Impact Factor). It leverages web scraping and academic APIs (PubMed, CrossRef, OpenAlex) to compile datasets, categorizes journals via machine learning clustering (K-Means & KNN), and generates visualizations mapping representation and publication length over time across various academic fields.

## Installation
1. Clone the repository and navigate to the root directory.
2. Ensure you have Python 3.9+ installed.
3. Establish a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install all required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a `.env` file in the root directory to store sensitive API variables:
   ```env
   PUBMED_API_KEY=your_key_here
   ```

## Usage
- **Data Gathering**: Run API scripts and scrapers within `src/scrape/` to populate `data/raw/` and `data/external/`.
- **Feature Engineering**: Execute identity inference scripts inside `src/features/` against raw author data.
- **Modeling**: Utilize scripts inside `src/models/` to classify journals based on their SJR scores and output to `data/processed/`.
- **Visualization**: Run scripts in `src/visualize/` to generate analytics charts.

## Project Structure
- `data/` - Contains raw, external, and processed CSV datasets.
- `docs/` - Project documentation.
- `notebooks/` - Exploratory Data Analysis.
- `src/` - Core Python modules separated by domain (scrape, features, models, visualize).
- `tests/` - Directory reserved for unit tests.
