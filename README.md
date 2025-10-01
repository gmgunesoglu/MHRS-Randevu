# MHRS-Randevu

MHRS-Randevu, Python programlama diliyle yazılmış, kullanıcıların MHRS'de randevu bulmalarına yardımcı bir araçtır. Kullanıcıların belirlediği kriterler üzerinden sistemde taramalar yapar ve uygun bir randevu bulunması haline randevu kaydını gerçekleştirir.

---

## Bu Araç Sayesinde...

- 7/24 Bilgisayarınızın başında olmadan...
- Tarih ve saat aralıkları belirleyerek ve önceliklendirerek...
- Uygun bir randevu bulabilirsiniz.

---

## Kurulum (Windows Kullanıcıları İçin)


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
