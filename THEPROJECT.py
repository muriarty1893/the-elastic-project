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
    
    # Ürün başlığını çekme (HTML yapısına göre değiştirilmesi gerekebilir)
    # Örneğin: <h1 class="product-title">Başlık</h1>
    title = soup.find('h1', class_='pr-new-br').text if soup.find('h1', class_='pr-new-br') else 'No Title'
    
    # Ürün açıklamasını çekme (HTML yapısına göre değiştirilmesi gerekebilir)
    # Örneğin: <div class="product-description">Açıklama</div>
    description = soup.find('div', class_='seo-content').text if soup.find('div', class_='seo-content') else 'No Description'
    
    # Ürün etiketlerini çekme (HTML yapısına göre değiştirilmesi gerekebilir)
    # Örneğin: <a class="tag">Etiket</a>
    #tags = [tag.text for tag in soup.find_all('a', class_='tag')]
    
    # Kullanıcı yorumlarını çekme (HTML yapısına göre değiştirilmesi gerekebilir)
    # Örneğin: <div class="comment-text">Yorum</div>
    #comments = [comment.text for comment in soup.find_all('div', class_='comment-text')]
    
    return {
        'title': title,
        'description': description,
        #'tags': tags,
        #'comments': comments
    }

# Örnek bir URL'den veri çekme (Trendyol ürün sayfası)
url = 'https://www.trendyol.com/hc-care/complex-bitkisel-sac-bakim-kompleksi-100-ml-p-7103578?boutiqueId=61&merchantId=110268&sav=true'
data = scrape_website(url)
print(data)

# Elasticsearch bağlantısı
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

def index_data(index_name, doc_type, data):
    es.index(index=index_name, doc_type=doc_type, body=data)

# Toplanan veriyi Elasticsearch'e indeksleme
index_data('products', 'product', data)

# Kullanıcı verilerini simüle etme
user_data = {
    'user_id': [1, 2, 3, 11, 22, 33],
    'search_query': ['laptop', 'phone', 'shirt', 'headphones', 'chair', 'shoes'],
    'click_product': [101, 102, 103, 104, 105, 106]
}

# Veriyi bir Pandas DataFrame'e dönüştürme
df = pd.DataFrame(user_data)

# Veriyi one-hot encoding ile hazırlama
df_encoded = pd.get_dummies(df, columns=['search_query'])

# Eğitim ve test verilerine ayırma
train = df_encoded.sample(frac=0.8, random_state=0)
test = df_encoded.drop(train.index)

# Giriş (X) ve çıkış (y) değişkenlerini ayırma
X_train = train.drop(['user_id', 'click_product'], axis=1)
y_train = train['click_product']
X_test = test.drop(['user_id', 'click_product'], axis=1)
y_test = test['click_product']

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
def recommend_products(user_search_query):
    user_query_encoded = pd.get_dummies(pd.DataFrame({'search_query': [user_search_query]}))
    missing_cols = set(X_train.columns) - set(user_query_encoded.columns)
    for col in missing_cols:
        user_query_encoded[col] = 0
    user_query_encoded = user_query_encoded[X_train.columns]
    predicted_product = model.predict(user_query_encoded)
    product_id = int(predicted_product[0][0])
    result = es.get(index='products', doc_type='product', id=product_id)
    return result['_source']

# Kullanıcıya öneri sunma
user_search_query = 'laptop'
recommended_product = recommend_products(user_search_query)
print(recommended_product)
