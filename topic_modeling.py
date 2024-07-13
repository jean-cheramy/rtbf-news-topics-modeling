# https://maartengr.github.io/BERTopic/getting_started/topicsovertime/topicsovertime.html#visualization
import nltk
from datetime import datetime
import pandas as pd
from scipy.cluster import hierarchy as sch
from bertopic import BERTopic

from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from preprocesser import clean_text, sort_timestamps
from bertopic import BERTopic
nltk.download('stopwords')
from nltk.corpus import stopwords


# topic word score all dataset
# topics distribution in all dataset (no time info)
# words clouds
# do something with the average article length per topic (do we write less article on politics but bigger ones?)
# numbers of articles written by journalists over time
# read all the dataset and put days limit to 180 or 365 by default
class TopicModeler:
    def __init__(self, dataset_path, n=2000, d=60):
        self.model = None
        self.dataset_path = dataset_path
        self.texts, self.datetime_objects = self.load_dataset(n, d)

    def load_dataset(self, n=2000, d=60):
        df = pd.read_csv(self.dataset_path, sep="\t")
        titles = [clean_text(t) for t in df["Title"].tolist()[:n]]
        texts = [clean_text(t) for t in df["Text"].tolist()[:n]]
        concatenated_titles_texts = [f"{a} {b}" for a, b in zip(titles, texts)]

        timestamps = df["PublishDate"].tolist()[:n]
        sorted_texts, sorted_datetime_objects = sort_timestamps(concatenated_titles_texts, timestamps, d)
        return sorted_texts, sorted_datetime_objects

    def load_file_model(self, model_path):
        self.model = BERTopic.load(model_path)

    def save_model(self, model_path):
        self.model.save(model_path)

    def extract_topics_over_time(self):
        topics_over_time = self.model.topics_over_time(self.texts, self.datetime_objects,
                                                       datetime_format=None,
                                                       global_tuning=True,
                                                       evolution_tuning=True,
                                                       nr_bins=20)
        fig_over_time = self.model.visualize_topics_over_time(topics_over_time, top_n_topics=20)
        fig_over_time.write_html("figures/fig_over_time.html")
        topics_over_time.to_csv("tableau_files/topics_over_time.csv", index=False, index_label=False)

    def extract_topics_stats(self):
        topics = self.model.get_topics()
        print(topics)
        dataframe_input = []
        for top, v in topics.items():
            for item in v:
                d = {
                    'TopicID': top,
                    'TopicName': self.model.custom_labels_[top+1],
                    'Word': item[0],
                    'Probability': item[1]
                }
                dataframe_input.append(d)

        new_df = pd.DataFrame(dataframe_input)
        new_df.to_csv("tableau_files/topics_stats.csv", index=False, index_label=False)

    def extract_hierarchical_topics(self):
        linkage_function = lambda x: sch.linkage(x, 'single', optimal_ordering=True)
        hierarchical_topics = self.model.hierarchical_topics(self.texts, linkage_function=linkage_function)
        hierarchical_topics.to_csv("tableau_files/hierarchical_topics.csv", index=False, index_label=False)

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

        today = datetime.today()
        self.save_model(f"models/model_{n}_{today.hour}_{today.minute}_{today.day}_{today.month}_{today.year}.pickle")


if __name__ == "__main__":
    n = 2000
    days = 28
    topic_modeler = TopicModeler("dataset/dataset_rtbf.csv", n, days)
    topic_modeler.topic_modeling(n)
    topic_modeler.extract_topics_stats()
    topic_modeler.extract_topics_over_time()
    topic_modeler.extract_hierarchical_topics()
    #topic_modeler.load_file_model()
