from transformers import pipeline, AutoTokenizer
from textblob import TextBlob
import string
import logging

logger = logging.getLogger(__name__)


def analyze(df):
    sentiment_analysis(df, hugging_face=False)
    text_summary(df)


def sentiment_analysis(df, hugging_face):
    if hugging_face:
        models = ['roberta-base', 'bert-base-uncased']
        for model in models:
            sentiment_pipeline = pipeline('sentiment-analysis', model=model)
            tokenizer = AutoTokenizer.from_pretrained(model)

            for song in df:
                lyrics = song.lyrics.lower()
                tokens = tokenizer(lyrics, truncation=True, max_length=512, return_tensors='tf')

                decoded_lyrics = tokenizer.decode(tokens['input_ids'].numpy().squeeze(), skip_special_tokens=True)
                sentiment = sentiment_pipeline(decoded_lyrics)
                return sentiment

    else:
        sentiment_scores = []
        for song in df:
            lyrics = song.lyrics.lower()
            lyrics = lyrics.translate(str.maketrans('', '', string.punctuation))

            analysis = TextBlob(lyrics)
            sentiment_value = analysis.sentiment.polarity

            sentiment_percentage = (sentiment_value + 1) * 50
            sentiment_scores.append(sentiment_percentage)

        sentiment = sum(sentiment_scores) / len(sentiment_scores)
        return sentiment


def text_summary(df):
    for song in df:
        lyrics = song.lyrics
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

        summary = summarizer(lyrics, max_length=150, min_length=50, do_sample=False)
        print(summary)

