import json
import time
from datetime import datetime
from pathlib import Path
from multiprocessing import Pool

import pandas as pd
import regex as re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def transform_date(date):
    if "il y a" or "aujourd'hui" in date:
        d = datetime.today()
        date = f"{d.day}/{d.month}/{d.year}"
    elif "hier" in date:
        d = datetime.today()
        date = f"{d.day-1}/{d.month}/{d.year}"
    else:
        d = date.split("à")[0].split(" ")
        date = f"{d[0]}/{d[1].lower().replace('.', '')}/{d[2]}"
    return date

#TODO
# write click function
# preprocessing function
# add type into arguments defition
# refactor code properly
# transform date properly
# add comments

class Scraper:
    def __init__(self, rtbf_url):
        self.dataset_file = "dataset_rtbf.csv"
        self.rtbf_url_prefix = "https://www.rtbf.be"
        self.title_xpath = "//*[@id='id-text2speech-article']/div[1]/header/div[1]/div/h1"
        self.date_xpath = "//*[@id='id-text2speech-article']/div[1]/header/div[3]/div/div/div[1]/span[1]"
        self.content_xpath = '//*[@id="content"]/div/div/div'
        self.reading_time_xpath = "//*[@id='id-text2speech-article']/div[1]/header/div[3]/div/div/div[1]/span[3]/time"
        self.tags_xpath = "//*[@id='id-text2speech-article']/div[7]/div/ul"
        self.en_continu_url = rtbf_url

        try:
            df = pd.read_csv(self.dataset_file, sep="\t")
            self.processed_urls = set([url.replace(self.rtbf_url_prefix, "") for url in df['URL'].tolist()])
        except:
            self.processed_urls = set()

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

            articles_urls = [url.get('href') for url in soup.find_all('a') if "article" in url.get('href')]
            to_process_urls = set(articles_urls).difference(set(self.processed_urls))
            print(len(to_process_urls))
            if len(to_process_urls) > 0:
                with Pool(processes=4) as pool:
                    results = pool.map(self.get_article_content_multi, to_process_urls)
                    self.update_csv_multi(results, to_process_urls)

        en_continu_driver.quit()

    def get_textual_content_from_xpath(self, driver, xpath):
        wait = WebDriverWait(driver, 10)
        try:
            element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            html = element.get_attribute('outerHTML')
            soup = BeautifulSoup(html, 'lxml')
            text = soup.get_text().strip()
            cleaned_text = re.sub(r'\u00A0', ' ', text)
            return cleaned_text
        except Exception as e:
            print(e)
            return ""

    def get_list_content_from_xpath(self, driver, xpath):
        wait = WebDriverWait(driver, 10)
        try:
            element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            html = element.get_attribute('outerHTML')
            soup = BeautifulSoup(html, 'lxml')
            ul_list = soup.find('ul')
            return [li.text for li in ul_list.find_all('li')]
        except Exception as e:
            print(e)
            return []

    def get_article_content_multi(self, url):
        driver = webdriver.Chrome()
        complete_url = self.rtbf_url_prefix+url
        driver.get(complete_url)

        title = self.get_textual_content_from_xpath(driver, self.title_xpath)
        date = self.get_textual_content_from_xpath(driver, self.date_xpath)
        content = self.get_textual_content_from_xpath(driver, self.content_xpath)
        reading_time = self.get_textual_content_from_xpath(driver, self.reading_time_xpath)
        tags = self.get_list_content_from_xpath(driver, self.tags_xpath)

        d = datetime.today()
        pattern = r'[\t\n]'
        url_id = re.split("-", complete_url)[-1]

        data = {
            'ID': url_id,
            'URL': complete_url,
            'Title': re.sub(pattern, ' ', title).replace("- RTBF Actus", ""),
            'Text': re.sub(pattern, ' ', content),
            'PublishDate': transform_date(date),
            'Tags': ",".join(tags),
            'ReadingTime': reading_time.replace("min", "").strip(),
            'ExtractionDate': f"{d.day}/{d.month}/{d.year}"
        }

        driver.quit()
        return data

    def update_csv_multi(self, docs, urls):
        file_path = Path(self.dataset_file)
        if file_path.exists():
            df = pd.read_csv(self.dataset_file, sep="\t")
            new_df = pd.concat([df, pd.DataFrame(docs)], ignore_index=True)
        else:
            new_df = pd.DataFrame(docs)
        new_df.to_csv(self.dataset_file, index=False, encoding='utf-8', sep="\t")
        self.processed_urls.update(urls)


if __name__ == "__main__":
    rtbf_url = "https://www.rtbf.be/en-continu"
    scraper = Scraper(rtbf_url)
    scraper.scrape()
