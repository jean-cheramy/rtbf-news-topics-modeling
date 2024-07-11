import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import regex as re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


#TODO
# write click function
# preprocess textual data properly (NBSP tag?) + preprocessing function
# refactor code properly
# add comments

class Scraper:
    def __init__(self, rtbf_url):
        self.dataset_file = "dataset_rtbf.csv"
        self.rtbf_url_prefix = "https://www.rtbf.be"
        self.en_continu_url = rtbf_url
        self.processed_urls = set()
        try:
            df = pd.read_csv(self.dataset_file, sep="\t")
            self.processed_urls_ids = set(df['ID'].tolist())
        except:
            self.processed_urls_ids = set()

    def scrape(self):
        not_encountered = True
        en_continu_driver = webdriver.Chrome()
        en_continu_driver.get(self.en_continu_url)
        # click cookies button: //*[@id="didomi-notice-agree-button"]
        cookies_button = WebDriverWait(en_continu_driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='didomi-notice-agree-button']"))
        )
        # Move to the element before clicking
        actions = ActionChains(en_continu_driver)
        actions.move_to_element(cookies_button).perform()
        time.sleep(1)

        # Click the "Load More" button
        cookies_button.click()

        while not_encountered:
            # Scroll to the bottom to trigger loading of more content
            en_continu_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # Find the "Load More" button element
            load_more_button = WebDriverWait(en_continu_driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='reach-skip-nav']/div[4]/div/div/div/div/button"))
            )
            # Move to the element before clicking
            actions = ActionChains(en_continu_driver)
            actions.move_to_element(load_more_button).perform()
            time.sleep(1)

            # Click the "Load More" button
            load_more_button.click()
            print("Charger plus d'articles")
            time.sleep(2)
            soup = BeautifulSoup(en_continu_driver.page_source, "lxml")
            # Process and save the data as needed
            article_driver = webdriver.Chrome()

            articles_urls = [url.get('href') for url in soup.find_all('a') if "article" in url.get('href')]
            to_process_urls = set(articles_urls).difference(set(self.processed_urls))
            #TODO multiprocess scraping of 20 new urls
            for url in to_process_urls:
                current_id = re.split("-", url)[-1]
                if current_id not in self.processed_urls_ids:
                    self.get_article_content(url, article_driver)
                else:
                    not_encountered = False
                    break
        en_continu_driver.quit()
        article_driver.quit()

    def get_article_content(self, url, driver):
        content_xpath = '//*[@id="content"]/div/div/div'
        complete_url = self.rtbf_url_prefix+url
        driver.get(complete_url)
        soup = BeautifulSoup(driver.page_source, "lxml")
        time.sleep(2)
        title = soup.find("title").text
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.presence_of_element_located((By.XPATH, content_xpath)))
        html = element.get_attribute('outerHTML')
        soup = BeautifulSoup(html, 'lxml')
        text = soup.get_text().strip()
        self.update_csv(title, text, url, complete_url)

    def update_csv(self, title, text, url, complete_url):
        d = datetime.today()
        pattern = r'[\t\n]'
        url_id = re.split("-", complete_url)[-1]
        data = [{
            'ID': url_id,
            'URL': complete_url,
            'Title': re.sub(pattern, ' ', title).replace("- RTBF Actus", ""),
            'Text': re.sub(pattern, ' ', text),
            'ExtractionDate': f"{d.day}/{d.month}/{d.year}"
        }]

        if url_id not in self.processed_urls_ids:
            file_path = Path(self.dataset_file)
            if file_path.exists():
                df = pd.read_csv(self.dataset_file, sep="\t")
                new_df = pd.concat([df, pd.DataFrame(data)], ignore_index=True)
            else:
                new_df = pd.DataFrame(data)

        new_df.to_csv(self.dataset_file, index=False, encoding='utf-8', sep="\t")
        self.processed_urls_ids.add(url_id)
        self.processed_urls.add(url)


if __name__ == "__main__":
    rtbf_url = "https://www.rtbf.be/en-continu"
    scraper = Scraper(rtbf_url)
    scraper.scrape()
