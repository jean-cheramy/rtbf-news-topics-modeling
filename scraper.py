import html
import json
import time
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path

import pandas as pd
import regex as re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# refactor and comments + method signature

def click(driver: WebDriver, xpath: str) -> None:
    """
    Finds an element by XPath and performs a click action after moving to the element.

    Args:
    - driver (WebDriver): The WebDriver instance used to interact with the web browser.
    - xpath (str): XPath expression to locate the element.

    Returns:
    - None
    """
    # Find the button
    button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    # Move to the element before clicking
    actions = ActionChains(driver)
    actions.move_to_element(button).perform()
    time.sleep(1)
    # Click the "Load More" button
    button.click()
    time.sleep(1)


class RTBFScraper:
    def __init__(self):
        """
        Initializes a RTBFScraper object.
        """
        self.dataset_file = "dataset/dataset_rtbf.csv"
        self.rtbf_url_prefix = "https://www.rtbf.be"
        self.en_continu_url = "https://www.rtbf.be/en-continu"
        self.load_more_xpath = "//*[@id='reach-skip-nav']/div[4]/div/div/div/div/button"
        self.cookies_xpath = "//*[@id='didomi-notice-agree-button']"

        # Attempt to read existing dataset to avoid re-processing URLs
        try:
            df = pd.read_csv(self.dataset_file, sep="\t")
            self.processed_urls = set([url.replace(self.rtbf_url_prefix, "") for url in df['URL'].tolist()])
        except FileNotFoundError:
            print(f"Error: Dataset file '{self.dataset_file}' not found.")
            self.processed_urls = set()
        except pd.errors.ParserError:
            print(f"Error: Unable to parse dataset file '{self.dataset_file}'. Check file format and encoding.")
            self.processed_urls = set()
        except Exception as e:
            print(f"Error occurred while loading dataset: {str(e)}")
            self.processed_urls = set()

    def scrape(self) -> None:
        """
        Initiates the scraping process for the RTBF webpage.
        """
        en_continu_driver = webdriver.Chrome()
        en_continu_driver.get(self.en_continu_url)
        # click cookies button
        click(en_continu_driver, self.cookies_xpath)

        while True:
            # Scroll to the bottom
            en_continu_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            # Click "Load More" button to fetch additional articles
            click(en_continu_driver, self.load_more_xpath)
            time.sleep(1)
            print("Charger plus d'articles...")
            # Parse the current page HTML with BeautifulSoup
            soup = BeautifulSoup(en_continu_driver.page_source, "lxml")
            # Extract URLs of articles from anchor tags
            articles_urls = [url.get('href') for url in soup.find_all('a') if "article" in url.get('href')]
            # Filter out already processed URLs
            to_process_urls = set(articles_urls).difference(set(self.processed_urls))
            print(len(to_process_urls))
            if len(to_process_urls) > 0:
                # Use multiprocessing to fetch article data concurrently
                with Pool(processes=4) as pool:
                    results = pool.map(self.get_article_requests_multi, to_process_urls)
                    self.update_csv_multi(results, to_process_urls)
            else:
                # No new articles to process, exit the loop and close the WebDriver
                en_continu_driver.quit()
                break

    def get_article_requests_multi(self, url: str) -> dict:
        """
        Retrieves and processes an article from a given URL.

        Args:
        - url (str): URL of the article.

        Returns:
        - dict: Processed data of the article.
        """
        complete_url = self.rtbf_url_prefix+url
        html_content = requests.get(complete_url).text

        # Parse the HTML content and Extract date from JSON-LD script
        soup = BeautifulSoup(html_content, 'html.parser')
        json_ld_scripts = soup.find_all('script', type='application/ld+json')

        # Loop through each script to find the correct one
        for script in json_ld_scripts:
            try:
                json_data = json.loads(script.string)
                if json_data.get('@type') == 'NewsArticle' and 'datePublished' in json_data:
                    # Extract relevant data from JSON-LD for the article
                    d = datetime.today()
                    url_id = re.split("-", complete_url)[-1]

                    return {
                        'ID': url_id,
                        'URL': complete_url,
                        'Title': html.unescape(json_data['headline']),
                        'Text': html.unescape(json_data['articleBody']),
                        'PublishDate': json_data['datePublished'],
                        'ModifiedDate': json_data['dateModified'],
                        'JournalistName': json_data['author']['name'],
                        'ExtractionDate': f"{d.day}/{d.month}/{d.year}"
                    }

            except json.JSONDecodeError:
                continue
        # Return empty dictionary if no valid data found
        return {}

    def update_csv_multi(self, docs: list, urls: set) -> None:
        """
        Updates the dataset CSV file with new articles.

        Args:
        - docs (list): List of dictionaries containing article data.
        - urls (list): List of URLs processed.

        Returns:
        - None
        """
        file_path = Path(self.dataset_file)
        docs_non_empty = [d for d in docs if d]
        if file_path.exists():
            # Append new data to existing CSV file
            df = pd.read_csv(self.dataset_file, sep="\t")
            new_df = pd.concat([df, pd.DataFrame(docs_non_empty)], ignore_index=True)
        else:
            # Create a new DataFrame if file doesn't exist
            new_df = pd.DataFrame(docs_non_empty)
        # Write updated DataFrame back to CSV file
        new_df.to_csv(self.dataset_file, index=False, encoding='utf-8', sep="\t")
        # Update processed URLs set with newly processed URLs
        self.processed_urls.update(urls)


if __name__ == "__main__":
    scraper = RTBFScraper()
    scraper.scrape()
