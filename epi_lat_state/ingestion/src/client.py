import os
import dotenv
import logging

import multiprocessing

from datetime import datetime
from chromedriver_py import binary_path

from dependencies.scraping.eProcIndLATState import EPILatestActiveStateTendersScraper
from dependencies.cleaning.EPI import clean_EPI
from dependencies.geocoding.epi import EPIGeocoder
from dependencies.standardization.epi import EPIStandardiser
from dependencies.es_ingestion.epi_ingestionv2 import EPIIngestion
from dependencies.utils import load_config_yaml

dotenv.load_dotenv(".env")
logging.basicConfig(level=logging.INFO)


def step_1():
    print("Number of CPUs found:", multiprocessing.cpu_count())
    path_config = load_config_yaml()["paths"]["EPILATS"]
    config = {
        "PROCESSES": multiprocessing.cpu_count() * 2,
        "executable_path": binary_path,
        "options": [
            "--headless",
            "--no-sandbox",
            "--start-fullscreen",
            "--allow-insecure-localhost",
            "--disable-dev-shm-usage",
        ],
        "drop_duplicates": ["tender_reference_number"],
        "epihvt_master_data_path": path_config["master_data_path"],
    }

    scraper = EPILatestActiveStateTendersScraper(config=config)
    scraper.run()
    logging.info("Scraped Raw data")


def step_2():
    extra_config = {"source_abbr": "EPILATS"}
    clean_EPI(extra_config=extra_config).run()
    logging.info("Cleaned Main Data")


def step_3():
    APIKEY = os.getenv("POSITION_STACK_API_KEY")
    path_config = load_config_yaml()["paths"]["EPILATS"]
    geomapper = EPIGeocoder(config=path_config, api_key=APIKEY)
    geomapper.run()
    logging.info("Geocoded Cleaned Data")


def step_4():
    path_config = load_config_yaml()["paths"]["EPILATS"]
    config = {
        "columns": [
            "product_category",
            "product_sub_category",
            "tender_category",
            "title",
        ],
        "geocoded_data_path": path_config["geocoded_data_path"],
        "standardised_data_path": path_config["standardized_data_path"],
        "metadata_path": path_config["metadata_path"],
    }
    standardizer = EPIStandardiser(config=config)
    standardizer.run()
    logging.info("Standardising Cleaned Data")


def step_5():
    path_config = load_config_yaml()["paths"]["EPILATS"]
    EPIIngestion(config=path_config).run()
    logging.info("Ingestion Data Done")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--step", help="step to be choosen for execution")

    args = parser.parse_args()

    eval(f"step_{args.step}()")

    logging.info(
        {
            "last_executed": str(datetime.now()),
            "status": "Pipeline executed successfully",
        }
    )