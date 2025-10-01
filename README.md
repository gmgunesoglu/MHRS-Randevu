# MHRS-Randevu

MHRS-Randevu, Python programlama diliyle yazılmış, kullanıcıların MHRS'de randevu bulmalarına yardımcı bir araçtır. Kullanıcıların belirlediği kriterler üzerinden sistemde taramalar yapar ve uygun bir randevu bulunması haline randevu kaydını gerçekleştirir.

---

## Bu Araç Sayesinde...

- Bilgisayarınızın başında sürekli randevu almaya çalışmadan...
- Tarih ve saat aralıkları belirleyerek ve önceliklendirerek...
- Bir türlü alamadığınız o randevuları alabilirsiniz.

---

## Kurulum (Windows Kullanıcıları İçin)

1. Proje klasörünü ZIP olarak indirin.
2. ZIP dosyasındaki "dist" klasörünü açın.
3. Bu klasördeki "main.exe" ve "mhrs_data.json" dosyalarını kendi belirlediğiniz bir klasöre çıkartın.
4. Kendi user-agent bilginizi öğrenin. Bir web tarayıcınızı açıp www.google.com/search?q=what+is+my+user-agent adresine giderek bu bilgiye ulaşabilirsiniz. Bu adresin size verdiği sonucu kopyalayın.
5. "mhrs_data.json" dosyasını not defterinde açın ve user-agent bilginizi çift tırnak içindeki yere yapıştırın, çift tırnaklar kalacak şekilde. Örnek: {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"}
6. "mhrs_data.json" dosyasını kaydedip kapatın.
7. main.exe dosyasını çalıştırın.

#### Eğer bu işlemleri doğru bir şekilde yaptıysanız TCKN ve Parola ile giriş yapmanızı bekleyen bir pencere ile karşılaşacaksınız. 

---

## Kurulum (Geliştiriciler İçin)

Aşağıdaki adımları takip ederek projeyi çalışır hale getirebilirsiniz:

```bash
# 1. Repo’yu klonla
git clone https://github.com/gmgunesoglu/MHRS-Randevu.git
cd MHRS-Randevu

# 2. Sanal ortam oluştur (opsiyonel ama önerilir)
python -m venv .venv
# Windows için:
.venv\Scripts\activate
# Unix/macOS için:
# source .venv/bin/activate

# 3. Gerekli paketleri yükle
pip install -r requirements.txt

⚠️ Not: "mhrs_data.json" dosyasını kendi user-agent bilginiz ile güncellemeyi unutmayın.

```

---

## Kullanım

Toplamda 5 farklı pencereden oluşan bu aracın kullanımı oldukça basittir.

1. Ekran: TCKN ve şireniz ile giriş yapın.
2. Ekran: İl ve Klinik alanları zorunlu olmak üzere, boş olan alanları doldurun. (MHRS'deki gibi...)
3. Ekran: Size uygun olan tarihleri sıralı bir şekilde seçin. Tarih seçimindeki sıralama dikkate alınır.
4. Ekran: Size uygun olan saatleri sıralı bir şekilde seçin. Saat seçiminizdeki sıralamada dikkate alınır.
5. Ekran: Randevu notunuz varsa ekleyin ve aramayı başlatın, randevu notunuz yoksa direkt başlatın. 

⚠️ Not: Eğer sistem sizin belirlediğiniz kriterlere uygun birden fazla randevu bulursa, tarih ve saat seçimi sıralamanızdaki önceliğe en yakın olan randevunun kaydını gerçekleştirir.

---

## Özellikler

- Kullanıcı dostu GUI: Tkinter ile basit ve anlaşılır arayüz
- Tarih ve saat filtreleme ve önceliklendirme
- Thread ile hızlı ve donmayan arayüz
- Google npt sunucusu ile zaman senkronizasyonu