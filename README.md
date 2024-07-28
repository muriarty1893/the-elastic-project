# Elastic-search Trendyol Scraper 

This project scrapes the best-selling gaming mice from Trendyol and indexes the data into Elasticsearch. It allows for fuzzy searching of the indexed products.

## :ledger: Index

- [About](#beginner-about)
- [Usage](#zap-usage)
  - [Installation](#electric_plug-installation)
  - [Commands](#package-commands)
- [Development](#wrench-development)
  - [Pre-Requisites](#notebook-pre-requisites)
  - [Development Environment](#nut_and_bolt-development-environment)
  - [File Structure](#file_folder-file-structure)
- [License](#lock-license)

## :beginner: About

This project scrapes data from Trendyol's best-selling gaming mice page, processes the data, and indexes it into an Elasticsearch instance. The indexed data can then be searched using fuzzy search capabilities.

## :zap: Usage

### :electric_plug: Installation

1. Clone the repository:
git clone https://github.com/yourusername/trendyol-scraper.git

2. Navigate to the project directory:
cd trendyol-scraper

3. Install the required Python packages:
pip install -r requirements.txt

4. Ensure you have Elasticsearch running locally or configure the connection parameters in the `create_elastic_client` function.

### :package: Commands

- To run the scraper and index data into Elasticsearch:
python trendyol_scraper.py

## :wrench: Development

### :notebook: Pre-Requisites

- Python 3.x
- Elasticsearch 7.x

### :nut_and_bolt: Development Environment

1. Clone the repository:
git clone https://github.com/yourusername/trendyol-scraper.git

2. Navigate to the project directory:
cd trendyol-scraper

3. Install the required Python packages:
pip install -r requirements.txt

4. Ensure you have Elasticsearch running locally or configure the connection parameters in the `create_elastic_client` function.

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

## :lock: License

Add a license here, or a link to it.
