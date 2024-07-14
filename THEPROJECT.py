import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense

# Web scraping fonksiyonu
def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.find('h1').text if soup.find('h1') else 'No Title'
    description = soup.find('p').text if soup.find('p') else 'No Description'
    tags = [tag.text for tag in soup.find_all('a', class_='tag')]
    return {'title': title, 'description': description, 'tags': tags}

# Örnek bir URL'den veri çekme
url = 'https://www.example.com/news_article'
data = scrape_website(url)
print(data)

# Elasticsearch bağlantısı
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

def index_data(index_name, doc_type, data):
    es.index(index=index_name, doc_type=doc_type, body=data)

# Toplanan veriyi Elasticsearch'e indeksleme
index_data('news', 'article', data)

# Kullanıcı verilerini simüle etme
user_data = {
    'user_id': [1, 2, 3, 1, 2, 3],
    'search_query': ['technology', 'health', 'technology', 'science', 'health', 'sports'],
    'click_article': [101, 102, 103, 101, 104, 105]
}

# Veriyi bir Pandas DataFrame'e dönüştürme
df = pd.DataFrame(user_data)

# Veriyi one-hot encoding ile hazırlama
df_encoded = pd.get_dummies(df, columns=['search_query'])

# Eğitim ve test verilerine ayırma
train = df_encoded.sample(frac=0.8, random_state=0)
test = df_encoded.drop(train.index)

# Giriş (X) ve çıkış (y) değişkenlerini ayırma
X_train = train.drop(['user_id', 'click_article'], axis=1)
y_train = train['click_article']
X_test = test.drop(['user_id', 'click_article'], axis=1)
y_test = test['click_article']

# Modeli oluşturma
model = Sequential([
    Dense(32, activation='relu', input_shape=(X_train.shape[1],)),
    Dense(16, activation='relu'),
    Dense(1)
])

# Modeli derleme
model.compile(optimizer='adam', loss='mean_squared_error')

# Modeli eğitme
model.fit(X_train, y_train, epochs=10, batch_size=1, verbose=1)

# Modeli değerlendirme
loss = model.evaluate(X_test, y_test)
print(f'Test Loss: {loss}')

# Öneri sistemi
def recommend_articles(user_search_query):
    user_query_encoded = pd.get_dummies(pd.DataFrame({'search_query': [user_search_query]}))
    missing_cols = set(X_train.columns) - set(user_query_encoded.columns)
    for col in missing_cols:
        user_query_encoded[col] = 0
    user_query_encoded = user_query_encoded[X_train.columns]
    predicted_article = model.predict(user_query_encoded)
    article_id = int(predicted_article[0][0])
    result = es.get(index='news', doc_type='article', id=article_id)
    return result['_source']

# Kullanıcıya öneri sunma
user_search_query = 'technology'
recommended_article = recommend_articles(user_search_query)
print(recommended_article)
