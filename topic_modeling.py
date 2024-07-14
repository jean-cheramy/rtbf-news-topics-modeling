from datetime import datetime

import nltk
import numpy as np
import pandas as pd
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance
from scipy.cluster import hierarchy as sch
from sklearn.feature_extraction.text import CountVectorizer

from preprocesser import clean_text, sort_timestamps

nltk.download('stopwords')
from nltk.corpus import stopwords

# refactor and comments + method signature


# create a chart number of articles per average length per article per topic per time
# group topics by similarity:
class TopicModeler:
    def __init__(self, dataset_path, d=90):
        self.model = None
        self.topics = None
        self.french_stop_words = stopwords.words('french')
        self.vectorizer = CountVectorizer(stop_words=self.french_stop_words, min_df=2, ngram_range=(1, 2))
        self.representation_model = MaximalMarginalRelevance(diversity=0.10, top_n_words=20)
        self.dataset_path = dataset_path
        self.texts, self.datetime_objects = self.load_dataset(d)

    def load_dataset(self, d=60):
        df = pd.read_csv(self.dataset_path, sep="\t")
        titles = [clean_text(t) for t in df["Title"].tolist()]
        texts = [clean_text(t) for t in df["Text"].tolist()]
        concatenated_titles_texts = [f"{a} {b}" for a, b in zip(titles, texts)]
        timestamps = df["PublishDate"].tolist()
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
        fig_over_time = self.model.visualize_topics_over_time(topics_over_time, top_n_topics=40)
        fig_over_time.write_html("figures/fig_over_time.html")
        topics_over_time.to_csv("tableau_files/topics_over_time.csv", index=False, index_label=False)

    def extract_topics_stats(self):
        topics = self.model.get_topics()
        dataframe_input = []
        for top, v in topics.items():
            for item in v:
                d = {
                    'TopicID': top,
                    'TopicName': self.model.custom_labels_[top + 1],
                    'Word': item[0],
                    'Probability': item[1]
                }
                dataframe_input.append(d)

        new_df = pd.DataFrame(dataframe_input)
        new_df.to_csv("tableau_files/topics_stats.csv", index=False, index_label=False)

    def docs_per_topic_log(self):
        topic_assignments = self.model.topics_

        for topic_id in range(len(self.model.get_topics())):
            topic_documents = [doc for doc, assigned_topic in zip(self.texts, topic_assignments) if
                               assigned_topic == topic_id]
            with open("logs/documents_topics_relevance.txt", "a+", encoding="utf-8") as f:
                f.write(f"Topic {self.model.topic_labels_[topic_id-1]}:\n")
                for doc in topic_documents[:20]:
                    f.write(f"- {doc}\n")

    def extract_hierarchical_topics(self):
        linkage_function = lambda x: sch.linkage(x, 'single', optimal_ordering=True)
        hierarchical_topics = self.model.hierarchical_topics(self.texts, linkage_function=linkage_function)
        hierarchical_topics.to_csv("tableau_files/hierarchical_topics.csv", index=False, index_label=False)

    def extract_average_length(self):
        # Calculate document lengths
        X = self.vectorizer.fit_transform(self.texts)
        doc_lengths = np.array(X.sum(axis=1)).flatten()
        df = pd.DataFrame({'Document': self.texts, 'Topic': self.topics, 'Document Length': doc_lengths})
        avg_lengths = df.groupby('Topic')['Document Length'].mean().reset_index()
        avg_lengths.to_csv('tableau_files/average_document_lengths_per_topic.csv', index=False)

    def topic_modeling(self):
        self.model = BERTopic(vectorizer_model=self.vectorizer,
                              representation_model=self.representation_model,
                              verbose=True,
                              min_topic_size=30,
                              calculate_probabilities=True,
                              n_gram_range=(1, 2),
                              language="french")
        print("model training...")
        self.topics, probs = self.model.fit_transform(self.texts)
        topic_labels = self.model.generate_topic_labels(nr_words=3,
                                                        topic_prefix=False,
                                                        word_length=10,
                                                        separator="_")
        self.model.set_topic_labels(topic_labels)

        # Get the topics for each document
        today = datetime.today()
        self.save_model(f"models/model_{today.hour}_{today.minute}_{today.day}_{today.month}_{today.year}.pickle")


if __name__ == "__main__":
    topic_modeler = TopicModeler("dataset/dataset_rtbf.csv")
    #topic_modeler.load_file_model("models/model_20_20_14_7_2024.pickle")
    topic_modeler.topic_modeling()
    topic_modeler.extract_topics_stats()
    topic_modeler.extract_topics_over_time()
    topic_modeler.extract_hierarchical_topics()
    topic_modeler.extract_average_length()
    topic_modeler.docs_per_topic_log()

# topic_model.visualize_topics()
