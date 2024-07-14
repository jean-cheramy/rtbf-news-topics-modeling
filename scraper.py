import json
import time
import html
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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# refactor and comments + method signature

def click(driver, xpath: str):
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


class Scraper:
    def __init__(self, rtbf_url: str):
        self.dataset_file = "dataset/dataset_rtbf.csv"
        self.rtbf_url_prefix = "https://www.rtbf.be"
        self.en_continu_url = rtbf_url
        self.load_more_xpath = "//*[@id='reach-skip-nav']/div[4]/div/div/div/div/button"
        self.cookies_xpath = "//*[@id='didomi-notice-agree-button']"

        try:
            df = pd.read_csv(self.dataset_file, sep="\t")
            self.processed_urls = set([url.replace(self.rtbf_url_prefix, "") for url in df['URL'].tolist()])
        except:
            self.processed_urls = set()

    def scrape(self) -> None:
        en_continu_driver = webdriver.Chrome()
        en_continu_driver.get(self.en_continu_url)
        # click cookies button
        click(en_continu_driver, self.cookies_xpath)

        while True:
            # Scroll to the bottom
            en_continu_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            click(en_continu_driver, self.load_more_xpath)
            time.sleep(1)
            print("Charger plus d'articles...")
            soup = BeautifulSoup(en_continu_driver.page_source, "lxml")
            # scrape and save the data
            articles_urls = [url.get('href') for url in soup.find_all('a') if "article" in url.get('href')]
            to_process_urls = set(articles_urls).difference(set(self.processed_urls))
            print(len(to_process_urls))
            if len(to_process_urls) > 0:
                with Pool(processes=4) as pool:
                    results = pool.map(self.get_article_requests_multi, to_process_urls)
                    self.update_csv_multi(results, to_process_urls)
            else:
                en_continu_driver.quit()
                break

    def get_article_requests_multi(self, url: str) -> dict:
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
        return {}

    def update_csv_multi(self, docs: list, urls: list):
        file_path = Path(self.dataset_file)
        docs_non_empty = [d for d in docs if d]
        if file_path.exists():
            df = pd.read_csv(self.dataset_file, sep="\t")
            new_df = pd.concat([df, pd.DataFrame(docs_non_empty)], ignore_index=True)
        else:
            new_df = pd.DataFrame(docs_non_empty)
        new_df.to_csv(self.dataset_file, index=False, encoding='utf-8', sep="\t")
        self.processed_urls.update(urls)


if __name__ == "__main__":
    rtbf_url = "https://www.rtbf.be/en-continu"
    scraper = Scraper(rtbf_url)
    scraper.scrape()
