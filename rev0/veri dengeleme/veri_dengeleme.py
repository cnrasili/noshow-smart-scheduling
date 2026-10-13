import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from imblearn.under_sampling import InstanceHardnessThreshold

# 1. Bir önceki adımda hazırladığımız temiz veriyi okuyoruz
df = pd.read_csv('temizlenmis_veri.csv')

# 2. Tabloyu Bağımsız (X) ve Bağımlı (y) değişkenler olarak ikiye ayırıyoruz
X = df.drop('No-show', axis=1) # No-show hariç her şey (Yaş, cinsiyet, hastalıklar vs.)
y = df['No-show']              # Sadece tahmin etmeye çalıştığımız hedef sütun

print("Dengeleme ÖNCESİ randevu dağılımı:")
print(y.value_counts())

# 3. IHT Algoritmasını hazırlıyoruz
# Makalede kullanacağımız asıl model Karar Ağacı (DecisionTree) olduğu için,
# IHT'nin de zor örnekleri bulurken Karar Ağacı mantığını kullanmasını istiyoruz.
iht = InstanceHardnessThreshold(
    estimator=DecisionTreeClassifier(random_state=42),
    random_state=42,
    cv=5
)

print("\nIHT algoritması çalışıyor... (Veri çok büyük olduğu için bu işlem bilgisayar hızına göre 1-2 dakika sürebilir, lütfen bekle!)")

# 4. Veriyi dengeliyoruz
X_dengeli, y_dengeli = iht.fit_resample(X, y)

print("\nDengeleme SONRASI randevu dağılımı:")
print(pd.Series(y_dengeli).value_counts())

# 5. Dengelenmiş X ve y'yi tekrar tek bir tablo (Excel) formatında birleştiriyoruz
df_dengeli = pd.DataFrame(X_dengeli, columns=X.columns)
df_dengeli['No-show'] = y_dengeli

# 6. Modelin eğitileceği nihai veriyi bilgisayara kaydediyoruz
df_dengeli.to_csv('dengelenmis_veri.csv', index=False)

print("\nHarika! %50 - %50 eşitlenmiş nihai veri 'dengelenmis_veri.csv' adıyla kaydedildi.")