import streamlit as st
import tweepy
import praw
import googleapiclient.discovery
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import time

# Configurazione pagina
st.set_page_config(
    page_title="Dashboard Sentiment Ucraina",
    page_icon="🌍",
    layout="wide"
)

# Titolo
st.title("Dashboard Analisi del Sentiment sull'Ucraina")
st.markdown("Analisi del sentiment da Twitter, Reddit e YouTube")

# Funzione per scaricare i dati NLTK necessari (eseguita solo una volta)
@st.cache_resource
def download_nltk_data():
    nltk.download('vader_lexicon')
    nltk.download('punkt')
    
download_nltk_data()

# Configurazione delle API
def setup_apis():
    # Twitter API
    twitter_bearer_token = "AAAAAAAAAAAAAAAAAAAAALo0zgEAAAAAXTEGLBKoFPgY5OdbYddT9Kw5Wdo%3DoXmyxe2RnjWdNFLgU5mUKr1MRCY1ousvRAnQ7tZpV5gKDJtH3t"
    twitter_access_token = "1894368025639612416-D84KgyOfEbjuCoaLJM00OHSHvX9JUJ"
    twitter_access_secret = "KUw6HdhdWc9C3Mu66UGaG4j3b4fTloTyDDkhVZonxirNr"
    
    twitter_client = tweepy.Client(
        bearer_token=twitter_bearer_token,
        access_token=twitter_access_token,
        access_token_secret=twitter_access_secret
    )
    
    # Reddit API
    reddit_client_id = "Px_In6BwjzEWS19-K8JJpg"
    reddit_client_secret = "siKy4kDN8PR4Snwu6xL2MSEKvdUFbA"
    reddit_username = "deville.gabriele.privato@gmail.com"
    reddit_password = "Gabriele2501"
    
    reddit = praw.Reddit(
        client_id=reddit_client_id,
        client_secret=reddit_client_secret,
        username=reddit_username,
        password=reddit_password,
        user_agent="sentiment_analysis_app/1.0"
    )
    
    # YouTube API
    youtube_api_key = "AIzaSyC8yOoLq6zJmyjxcLrCVYR7hP54vPdgsrA"
    youtube = googleapiclient.discovery.build(
        "youtube", "v3", developerKey=youtube_api_key
    )
    
    return twitter_client, reddit, youtube

# Funzione per raccogliere tweet sull'Ucraina
def get_tweets(client):
    query = "Ukraine OR Ucraina OR guerra Ucraina -is:retweet"
    tweets = []
    
    try:
        for tweet in tweepy.Paginator(
            client.search_recent_tweets,
            query=query,
            max_results=100
        ).flatten(limit=100):  # Limitato a 100 per la versione Streamlit
            tweets.append(tweet.text)
    except Exception as e:
        st.error(f"Errore durante la raccolta dei tweet: {e}")
    
    return tweets

# Funzione per raccogliere post da Reddit sull'Ucraina
def get_reddit_posts(reddit):
    subreddits = ["ukraine", "UkraineWarVideoReport", "worldnews", "europe"]
    posts = []
    
    try:
        for subreddit_name in subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            for post in subreddit.search("Ukraine OR Ucraina", limit=25):
                posts.append(post.title)
                if post.selftext:
                    posts.append(post.selftext)
    except Exception as e:
        st.error(f"Errore durante la raccolta dei post Reddit: {e}")
                
    return posts

# Funzione per raccogliere commenti dai video di YouTube sull'Ucraina
def get_youtube_comments(youtube):
    search_response = youtube.search().list(
        q="Ukraine war",
        part="id,snippet",
        maxResults=10,
        type="video"
    ).execute()
    
    comments = []
    for item in search_response.get("items", []):
        video_id = item["id"]["videoId"]
        
        try:
            comments_response = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=25
            ).execute()
            
            for comment in comments_response.get("items", []):
                comment_text = comment["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment_text)
        except:
            # Alcuni video potrebbero avere i commenti disabilitati
            continue
            
    return comments

# Funzione per analizzare il sentiment di un testo
def analyze_sentiment(texts):
    sid = SentimentIntensityAnalyzer()
    results = []
    
    for text in texts:
        try:
            sentiment_scores = sid.polarity_scores(text)
            compound = sentiment_scores['compound']
            
            if compound >= 0.05:
                sentiment = "positivo"
            elif compound <= -0.05:
                sentiment = "negativo"
            else:
                sentiment = "neutro"
                
            results.append({
                "text": text[:100] + "..." if len(text) > 100 else text,
                "compound": compound,
                "sentiment": sentiment
            })
        except:
            continue
        
    return pd.DataFrame(results)

# Funzione principale per raccogliere e analizzare i dati
@st.cache_data(ttl=43200)  # Cache per 12 ore (43200 secondi)
def collect_and_analyze_data():
    with st.spinner('Raccolta dati in corso...'):
        twitter_client, reddit, youtube = setup_apis()
        
        # Raccolta dati
        tweets = get_tweets(twitter_client)
        reddit_posts = get_reddit_posts(reddit)
        youtube_comments = get_youtube_comments(youtube)
        
        # Analisi del sentiment
        twitter_df = analyze_sentiment(tweets)
        twitter_df['source'] = 'Twitter'
        
        reddit_df = analyze_sentiment(reddit_posts)
        reddit_df['source'] = 'Reddit'
        
        youtube_df = analyze_sentiment(youtube_comments)
        youtube_df['source'] = 'YouTube'
        
        # Unione dei DataFrame
        combined_df = pd.concat([twitter_df, reddit_df, youtube_df])
        
        return combined_df, datetime.now()

# Barra laterale con info e comandi
with st.sidebar:
    st.title("Controlli Dashboard")
    
    # Pulsante per forzare aggiornamento dati
    if st.button("Aggiorna Dati Ora"):
        st.cache_data.clear()
        st.experimental_rerun()
    
    st.markdown("---")
    st.markdown("### Informazioni")
    st.markdown("Questa dashboard analizza il sentiment delle discussioni sull'Ucraina da diverse fonti social.")
    st.markdown("I dati vengono aggiornati automaticamente ogni 12 ore.")
    st.markdown("---")
    st.markdown("Sviluppato da: Gabriele Albanese")
    
# Carica o aggiorna i dati
df, last_update = collect_and_analyze_data()
next_update = last_update + timedelta(hours=12)

# Mostra le informazioni sull'aggiornamento
col1, col2 = st.columns(2)
with col1:
    st.info(f"**Ultimo aggiornamento:** {last_update.strftime('%d/%m/%Y %H:%M:%S')}")
with col2:
    st.info(f"**Prossimo aggiornamento:** {next_update.strftime('%d/%m/%Y %H:%M:%S')}")

# Statistiche principali
st.markdown("## Statistiche Principali")
col1, col2, col3 = st.columns(3)

with col1:
    total = len(df)
    st.metric("Totale Contenuti Analizzati", f"{total:,}")

with col2:
    positive_pct = (df['sentiment'] == 'positivo').mean() * 100
    st.metric("Percentuale Sentiment Positivo", f"{positive_pct:.1f}%")

with col3:
    negative_pct = (df['sentiment'] == 'negativo').mean() * 100
    st.metric("Percentuale Sentiment Negativo", f"{negative_pct:.1f}%")

# Grafici principali
st.markdown("## Grafici")

col1, col2 = st.columns(2)

with col1:
    # Grafico a torta per la distribuzione del sentiment
    sentiment_counts = df['sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['sentiment', 'count']
    
    fig_pie = px.pie(
        sentiment_counts, 
        values='count', 
        names='sentiment', 
        color='sentiment',
        color_discrete_map={
            'positivo': '#28a745',
            'neutro': '#6c757d',
            'negativo': '#dc3545'
        },
        title="Distribuzione complessiva del sentiment"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # Grafico a barre per sentiment per fonte
    sentiment_by_source = df.groupby(['source', 'sentiment']).size().reset_index(name='count')
    
    fig_bar = px.bar(
        sentiment_by_source,
        x='source',
        y='count',
        color='sentiment',
        barmode='group',
        color_discrete_map={
            'positivo': '#28a745',
            'neutro': '#6c757d',
            'negativo': '#dc3545'
        },
        title="Confronto del sentiment tra le diverse fonti",
        labels={'source': 'Fonte', 'count': 'Numero di contenuti', 'sentiment': 'Sentiment'}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Contenuti di esempio
st.markdown("## Esempi di Contenuti per Tipo di Sentiment")

tab1, tab2, tab3 = st.tabs(["Contenuti Positivi", "Contenuti Neutrali", "Contenuti Negativi"])

with tab1:
    positive_df = df[df['sentiment'] == 'positivo'].sample(min(5, sum(df['sentiment'] == 'positivo')))
    for i, row in positive_df.iterrows():
        st.markdown(f"**[{row['source']}]** {row['text']}")
        st.markdown("---")

with tab2:
    neutral_df = df[df['sentiment'] == 'neutro'].sample(min(5, sum(df['sentiment'] == 'neutro')))
    for i, row in neutral_df.iterrows():
        st.markdown(f"**[{row['source']}]** {row['text']}")
        st.markdown("---")

with tab3:
    negative_df = df[df['sentiment'] == 'negativo'].sample(min(5, sum(df['sentiment'] == 'negativo')))
    for i, row in negative_df.iterrows():
        st.markdown(f"**[{row['source']}]** {row['text']}")
        st.markdown("---")

# Analisi per fonte
st.markdown("## Analisi dettagliata per fonte")
source = st.selectbox("Seleziona la fonte da analizzare", df['source'].unique())

# Filtra i dati per la fonte selezionata
source_df = df[df['source'] == source]

col1, col2 = st.columns(2)

with col1:
    # Grafico a torta per la distribuzione del sentiment nella fonte selezionata
    source_sentiment = source_df['sentiment'].value_counts().reset_index()
    source_sentiment.columns = ['sentiment', 'count']
    
    fig_source_pie = px.pie(
        source_sentiment, 
        values='count', 
        names='sentiment', 
        color='sentiment',
        color_discrete_map={
            'positivo': '#28a745',
            'neutro': '#6c757d',
            'negativo': '#dc3545'
        },
        title=f"Distribuzione del sentiment su {source}"
    )
    st.plotly_chart(fig_source_pie, use_container_width=True)

with col2:
    # Statistiche per la fonte selezionata
    total_source = len(source_df)
    pos_source = sum(source_df['sentiment'] == 'positivo')
    neg_source = sum(source_df['sentiment'] == 'negativo')
    neu_source = sum(source_df['sentiment'] == 'neutro')
    
    st.markdown(f"### Statistiche per {source}")
    st.markdown(f"**Totale contenuti:** {total_source}")
    st.markdown(f"**Contenuti positivi:** {pos_source} ({pos_source/total_source*100:.1f}%)")
    st.markdown(f"**Contenuti neutrali:** {neu_source} ({neu_source/total_source*100:.1f}%)")
    st.markdown(f"**Contenuti negativi:** {neg_source} ({neg_source/total_source*100:.1f}%)")

# Piè di pagina
st.markdown("---")
st.markdown("Dashboard creata con Streamlit. Dati aggiornati automaticamente ogni 12 ore.")
