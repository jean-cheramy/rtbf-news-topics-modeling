# becode-ds-challenge

This repository contains Python scripts for scraping the RTBF en-continu website and performing topic modeling on the collected articles.

## Description

### Web Scraper:
- Python script (`scraper.py`) for scraping articles from the RTBF en-continu website.
- Utilizes BeautifulSoup for parsing HTML.
- Uses Selenium for interacting with dynamic elements and navigating through the website.
- Scrapes article content, title, date.

### Topic Modeling:
- Python script (`topic_modeling.py`) for topic modeling on the scraped articles.
- Uses natural language processing techniques and libraries like BERTopic, NLTK and sklearn.
- Implements BERTopic model to discover latent topics within the article corpus.
- Export topics, probabilities and their distributions into csv files to upload them into Tableau.

## Usage

- Clone the repository and install the necessary dependencies (`requirements.txt`).
- Run `scraper.py` to collect articles from RTBF en-continu and update the dataset.
- Run `topic_modeling.py` to perform topic modeling on the collected data.

## Deployed Tableau instructions
https://public.tableau.com/views/RTBFactus/RTBFNews-Story?:language=fr-FR&:sid=0590D56B23E94853A5C8D1D8EC4CE3CB-0:0&:redirect=auth&:display_count=n&:origin=viz_share_link

## Improvements:
- Performance:
  - performance optimization for model training (parallelize computations and speed up training to handle larger and growing datasets)
  - improve sorting function for larger datasets
- Accuracy:
  - take articles updates into account to update the record in the dataset
  - use OpenAI models to boost topics relevance (ada embeddings) or at least generate keywords to describe topics (but API not free)
  - use french model instead of a multilingual
- Features:
  - create a chart to see the numbers of articles per topic written by journalists over time 
  - create a chart to see, per category, the frequency of articles vs. the average length over time (see the effect of a shading trend or effect of a new trend on another one)
  - group topics by semantic similarity
  - enable interaction on Tableau with time periods to be able to see a new topic which would not be present on the 3 months dashboard because we need a minimum numbers of occurrences to create a topic
  - extract and use rtbf categories as a "group" of topics to have a general overview (most frequent categories in topics). For example football + tennis + tour de france topics are in sports category
- Other:
  - improve exceptions management (depending on a production strategy)
  - plan to update the model with new scrapped articles to avoid training the model from scratch while updating
  - lemmatize most frequents words to avoid words duplication (palestinien, palestiniens, palestiniennes -> palestinien)

## To Production
- deploy python code into AWS lambdas + encapsulate them into Stepfunctions to manage errors and create a process:
  - scraping
  - preprocessing + topics modeling or updating and files saving (model and csv)
- create an EventBridge to launch the stepfunctions once a week
- store Power BI input files in AWS S3 (csv)
- link PowerBI to AWS S3 and refresh report once a week 
- be able to update the model with new records to match a regular-basis update
- OR do it in Microsoft Azure as PowerBI is native in this environment
## Timeline
- scraper: 3 Hours
- Topic Modeling: 2 Hours
- Tableau: 2 Hours
