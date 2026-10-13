import pandas as pd

# 1. Veriyi okuma ve gereksiz kimlikleri silme
df = pd.read_csv('data.csv')
df = df.drop(['PatientId', 'AppointmentID'], axis=1)

# 2. Tarihleri çevirme ve saatleri sıfırlama
df['ScheduledDay'] = pd.to_datetime(df['ScheduledDay']).dt.normalize()
df['AppointmentDay'] = pd.to_datetime(df['AppointmentDay']).dt.normalize()

# 3. Lead Time (Hazırlık Süresi) hesaplama
df['LeadTime'] = (df['AppointmentDay'] - df['ScheduledDay']).dt.days

# 4. Hatalı LeadTime ve Yaş kayıtlarını silme
df = df[df['LeadTime'] >= 0]
df = df[(df['Age'] >= 0) & (df['Age'] < 120)]

# İşi biten eski tarih sütunlarını silme
df = df.drop(['ScheduledDay', 'AppointmentDay'], axis=1)

# *** YENİ ADIM 5: METİNLERİ SAYILARA ÇEVİRME (ENCODING) ***

# Cinsiyeti sayılara çeviriyoruz: F = 1, M = 0
df['Gender'] = df['Gender'].map({'F': 1, 'M': 0})

# Randevuya gelmeme durumunu sayılara çeviriyoruz: Yes = 1, No = 0
df['No-show'] = df['No-show'].map({'Yes': 1, 'No': 0})

# Mahalle isimlerini otomatik olarak 0'dan başlayan sayılara dönüştürüyoruz
df['Neighbourhood'] = df['Neighbourhood'].astype('category').cat.codes

# 6. Tablonun son halini bilgisayara kaydetme
df.to_csv('temizlenmis_veri.csv', index=False)

print("Metinler başarıyla sayılara çevrildi! Artık tamamen matematiksel bir matrisimiz var.")
print("\nİşte tablonun ilk 5 satırı:")
print(df.head())