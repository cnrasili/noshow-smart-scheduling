import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.tree import DecisionTreeClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# 1. Dengelenmiş veriyi okuyoruz
df = pd.read_csv('dengelenmis_veri.csv')
X = df.drop('No-show', axis=1)
y = df['No-show']

# 2. Makaledeki Tablo III'e sadık kalarak en güçlü K=1 özelliğini seçiyoruz
selector = SelectKBest(score_func=f_classif, k=1)
X_selected = selector.fit_transform(X, y)

secilen_ozellik = X.columns[selector.get_support()][0]
print(f"Makalenin %95 başarı için bulduğu en kritik özellik: {secilen_ozellik}\n")

# 3. Eğitim ve Test olarak %80 - %20 ayırma
X_train, X_test, y_train, y_test = train_test_split(X_selected, y, test_size=0.2, random_state=42)

# 4. YENİ: class_weight='balanced' (Modeli zorlayan komut)
dt_model = DecisionTreeClassifier(random_state=42, class_weight='balanced')
param_grid = {'min_samples_split': [1000, 1400, 1800, 2000, 2200]}

print("Model sadece en iyi özellikle ve dengeli ağırlıkla (balanced) tekrar eğitiliyor...")
grid_search = GridSearchCV(dt_model, param_grid, cv=5, scoring='f1')
grid_search.fit(X_train, y_train)

# 5. Tahmin ve Sonuçları Yazdırma
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)

print("\n--- YENİ MODEL TEST SONUÇLARI ---")
print(f"Bulunan En İyi Parametre: {grid_search.best_params_}")
print(f"Doğruluk (Accuracy):  %{accuracy_score(y_test, y_pred) * 100:.1f}")
print(f"Kesinlik (Precision): %{precision_score(y_test, y_pred) * 100:.1f}")
print(f"Duyarlılık (Recall):  %{recall_score(y_test, y_pred) * 100:.1f}")
print(f"F1-Skoru:             %{f1_score(y_test, y_pred) * 100:.1f}")