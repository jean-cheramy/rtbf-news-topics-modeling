# https://maartengr.github.io/BERTopic/getting_started/topicsovertime/topicsovertime.html#visualization
import nltk
from datetime import datetime
import pandas as pd

from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer

from preprocesser import clean_text, sort_timestamps
from bertopic import BERTopic
nltk.download('stopwords')
from nltk.corpus import stopwords


# comparer diversity 0.2, 0.3, 0.4, 0.5
# concatenate title + description as the title contains valuable information
# display keywords and top-words for each topic
# show topics distribution
# words clouds
# topic evolution over time
# numbers of articles written by journalists over time
# use GPT to boost topics relevance
# read all the dataset and put days limit to 60 by default
class TopicModeler:
    def __init__(self, dataset_path, n=2000, d=60):
        df = pd.read_csv(dataset_path, sep="\t")
        titles = [clean_text(t) for t in df["Title"].tolist()[:n]]
        texts = [clean_text(t) for t in df["Text"].tolist()[:n]]
        concatenated_titles_texts = [f"{a} {b}" for a, b in zip(titles, texts)]

        timestamps = df["PublishDate"].tolist()[:n]
        self.texts, self.datetime_objects = sort_timestamps(concatenated_titles_texts, timestamps, d)

    def load_model(self, model_path):
        self.model = BERTopic.load(path=model_path)

    def save_model(self, model_path):
        self.model.save(model_path)

    def topic_modeling(self, n):
        french_stop_words = stopwords.words('french')
        vectorizer = CountVectorizer(stop_words=french_stop_words)
        representation_model = MaximalMarginalRelevance(diversity=0.20)
        self.model = BERTopic(vectorizer_model=vectorizer,
                               representation_model=representation_model,
                               verbose=True,
                               language="french")
        print("model training...")
        topics, probs = self.model.fit_transform(self.texts)
        topic_labels = self.model.generate_topic_labels(nr_words=3,
                                                         topic_prefix=False,
                                                         word_length=10,
                                                         separator="_")
        self.model.set_topic_labels(topic_labels)

        topics_over_time = self.model.topics_over_time(self.texts, self.datetime_objects,
                                                        datetime_format=None,
                                                        global_tuning=True,
                                                        evolution_tuning=True,
                                                        nr_bins=50)
        fig_over_time = self.model.visualize_topics_over_time(topics_over_time, top_n_topics=20)
        fig_over_time.write_html("fig_over_time.html")
        topics_over_time.to_csv("powerbi_files/input_power_bi_with_outliers.csv")
        today = datetime.today()
        self.save_model(f"models/model_{n}_{today.hour}_{today.minute}_{today.day}_{today.month}_{today.year}.pickle")


if __name__ == "__main__":
    n = 2000
    days = 28
    topic_modeler = TopicModeler("dataset/dataset_rtbf.csv", n, days)
    topic_modeler.topic_modeling(n)
