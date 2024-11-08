# Elastic-search Implementation Project

This project scrapes the best-selling gaming mouse from Trendyol website and indexes the data into Elasticsearch to use the search engine. It allows for fuzzy searching of the indexed products.

## :ledger: Index

- [Usage](#zap-usage)
  - [Installation](#electric_plug-installation)
  - [Commands](#package-commands)
- [Development](#wrench-development)
  - [Pre-Requisites](#notebook-pre-requisites)
  - [Development Environment](#nut_and_bolt-development-environment)
  - [File Structure](#file_folder-file-structure)
- [License](#lock-license)

## :zap: Usage

### :electric_plug: Installation

1. Clone the repository:
git clone https://github.com/yourusername/trendyol-scraper.git

2. Navigate to the project directory:
cd trendyol-scraper

3. Install the required Python packages:
pip install -r requirements.txt

4. Ensure you have Elasticsearch running locally and configure the connection parameters in the `create_elastic_client` function.

### :package: Commands

- To run the scraper, index data into Elasticsearch and searching:
python trendyol_scraper.py

## :wrench: Development

### :notebook: Pre-Requisites

- Python 3.x
- Elasticsearch 7.x

### :file_folder: File Structure
.

├── flags

│ └── indexing_done_37.flag # Flag file to check if indexing is done

├── trendyol_scraper.py # Main Python script

├── requirements.txt # Python dependencies

└── README.md # This file

| No | File Name | Details |
|----|------------|-------|
| 1  | trendyol_scraper.py | Main script to scrape data and index into Elasticsearch |
| 2  | requirements.txt | List of Python dependencies |
| 3  | README.md | Project documentation |
