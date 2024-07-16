from datetime import datetime

import nltk
import numpy as np
import pandas as pd
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer

from preprocesser import clean_text, sort_timestamps

# Download NLTK stopwords for French
nltk.download('stopwords')
from nltk.corpus import stopwords


class TopicModeler:
    def __init__(self, dataset_path: str, d: int = 90):
        """
        Initialize the TopicModeler object.

        Args:
        - dataset_path (str): Path to the dataset CSV file.
        - d (int): Number of days of data to consider for temporal analysis (default is 90).
        """
        self.model = None
        self.topics = None
        self.french_stop_words = stopwords.words('french')
        self.vectorizer = CountVectorizer(stop_words=self.french_stop_words, min_df=2, ngram_range=(1, 2))
        self.representation_model = MaximalMarginalRelevance(diversity=0.10, top_n_words=20)
        self.dataset_path = dataset_path
        self.texts, self.datetime_objects = self.load_dataset(d)

    def load_dataset(self, d: int = 90):
        """
        Load and preprocess the dataset.

        Args:
        - d (int): Number of days of data to consider for temporal analysis.

        Returns:
        - sorted_texts (list): Preprocessed texts sorted by timestamps.
        - sorted_datetime_objects (list): Datetime objects corresponding to the sorted texts.
        """
        try:
            df = pd.read_csv(self.dataset_path, sep="\t")
            titles = [clean_text(t) for t in df["Title"].tolist()]
            texts = [clean_text(t) for t in df["Text"].tolist()]
            concatenated_titles_texts = [f"{a} {b}" for a, b in zip(titles, texts)]
            timestamps = df["PublishDate"].tolist()
            sorted_texts, sorted_datetime_objects = sort_timestamps(concatenated_titles_texts, timestamps, d)
            return sorted_texts, sorted_datetime_objects
        except FileNotFoundError:
            print(f"Error: Dataset file '{self.dataset_path}' not found.")
            return [], []
        except pd.errors.ParserError:
            print(f"Error: Unable to parse dataset file '{self.dataset_path}'. Check file format and encoding.")
            return [], []
        except Exception as e:
            print(f"Error occurred while loading dataset: {str(e)}")
            return [], []

    def load_file_model(self, model_path):
        """
        Load a pre-trained BERTopic model from a file.

        Args:
        - model_path (str): Path to the saved BERTopic model file (.pickle).
        """
        self.model = BERTopic.load(model_path)

    def save_model(self, model_path):
        """
        Save the current BERTopic model to a file.

        Args:
        - model_path (str): Path to save the BERTopic model (.pickle).
        """
        self.model.save(model_path)

    def extract_topics_over_time(self):
        """
        Extract topics over time.
        """
        topics_over_time = self.model.topics_over_time(self.texts, self.datetime_objects,
                                                       datetime_format=None,
                                                       global_tuning=True,
                                                       evolution_tuning=True,
                                                       nr_bins=20)
        topics_over_time.to_csv("tableau_files/topics_over_time.csv", index=False, index_label=False)

    def extract_topics_stats(self):
        """
        Extract and save statistics for each topic.
        """
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
        """
        Log documents per topic to a file to check topics relevance manually.
        """
        topic_assignments = self.model.topics_

        for topic_id in range(len(self.model.get_topics())):
            topic_documents = [doc for doc, assigned_topic in zip(self.texts, topic_assignments) if
                               assigned_topic == topic_id]
            # Append topic documents to a log file
            with open("logs/documents_topics_relevance.txt", "a+", encoding="utf-8") as f:
                f.write(f"Topic {self.model.topic_labels_[topic_id-1]}:\n")
                for doc in topic_documents[:20]:
                    f.write(f"- {doc}\n")

    def extract_average_length(self):
        """
        Calculate and save the average document length per topic to a CSV file.
        """
        # Calculate document lengths using the vectorizer
        X = self.vectorizer.fit_transform(self.texts)
        doc_lengths = np.array(X.sum(axis=1)).flatten()
        df = pd.DataFrame({'Document': self.texts, 'Topic': self.topics, 'Document Length': doc_lengths})
        avg_lengths = df.groupby('Topic')['Document Length'].mean().reset_index()
        avg_lengths.to_csv('tableau_files/average_document_lengths_per_topic.csv', index=False)

    def topic_modeling(self):
        """
        Perform topic modeling using BERTopic and save the model.
        """
        self.model = BERTopic(vectorizer_model=self.vectorizer,
                              representation_model=self.representation_model,
                              verbose=True,
                              min_topic_size=30,
                              calculate_probabilities=True,
                              n_gram_range=(1, 2),
                              language="french")
        # Fit the BERTopic model to the texts and generate topic labels
        print("model training...")
        self.topics, probs = self.model.fit_transform(self.texts)
        topic_labels = self.model.generate_topic_labels(nr_words=3,
                                                        topic_prefix=False,
                                                        word_length=10,
                                                        separator="_")
        self.model.set_topic_labels(topic_labels)
        # Save the trained model with a timestamp
        today = datetime.today()
        self.save_model(f"models/model_{today.hour}_{today.minute}_{today.day}_{today.month}_{today.year}.pickle")


if __name__ == "__main__":
    topic_modeler = TopicModeler("dataset/dataset_rtbf.csv")
    # topic_modeler.load_file_model("models/model_13_1_15_7_2024.pickle")
    topic_modeler.topic_modeling()
    topic_modeler.extract_topics_stats()
    topic_modeler.extract_topics_over_time()
    topic_modeler.extract_average_length()
    topic_modeler.docs_per_topic_log()
