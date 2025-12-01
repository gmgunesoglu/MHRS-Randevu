import requests
from model import *
import json
import logging
import time
import base64


def _b64url_decode(s: str) -> bytes:
    s = s.replace('-', '+').replace('_', '/')
    padding = len(s) % 4
    if padding:
        s += '=' * (4 - padding)
    return base64.b64decode(s)

def relog_aspect(func):
    def wrapper(self, *args, **kwargs):  # self burada metot örneği
        parts = self.jwt.split('.')
        exp = json.loads(_b64url_decode(parts[1]).decode('utf-8'))["exp"]
        if (int(exp) - int(time.time())) < 3600:
            self.login(self.username, self.password)
            logging.info("JWT yenileme işlemi başarılı.")
        return func(self, *args, **kwargs)
    return wrapper


class MHRSClient:
    username = ""
    password = ""
    jwt = ""

    def __init__(self, headers):
        self.headers = headers

    def login(self, username: str, password: str) -> None:
        url = "https://prd.mhrs.gov.tr/api/vatandas/login"
        payload = {
          "kullaniciAdi": username,
          "parola": password,
          "islemKanali": "VATANDAS_RESPONSIVE",
          "girisTipi": "PAROLA",
          "captchaKey": None
        }
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            parsed_response = json.loads(response.text)
            self.jwt = parsed_response["data"]["jwt"]
            self.headers["Authorization"] = f'Bearer {self.jwt}'
            self.username = username
            self.password = password
        elif response.status_code == 428:
            raise RuntimeError(f"Giriş bilgileri birkaç kez hatalı girildiği için reCAPTCHA engeliyle karşılaşıldı. Yaklaşık on dakika beklendikten sonra tekrar deneyiniz.")
        else:
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_cities(self) -> List[City]:
        url = "https://prd.mhrs.gov.tr/api/yonetim/genel/il/selectinput-tree"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            return City.flatten(data)
        else:
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_towns(self, city: City) -> List[Town]:
        url = f"https://prd.mhrs.gov.tr/api/yonetim/genel/ilce/selectinput/{city.value}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            return [Town.from_dict(item) for item in data]
        else:
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_clinics(self, city: City, town: Town | None) -> List[Clinic]:
        town_id = -1 if town is None else town.value
        url = f"https://prd.mhrs.gov.tr/api/kurum/kurum/kurum-klinik/il/{city.value}/ilce/{town_id}/kurum/-1/aksiyon/200/randevuTuru/-1/select-input"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()["data"]
            return Clinic.flatten(data)
        else:
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_hospitals(self, city: City, town: Town | None, clinic: Clinic) -> List[Hospital]:
        town_id = -1 if town is None else town.value
        url = f"https://prd.mhrs.gov.tr/api/kurum/kurum/kurum-klinik/il/{city.value}/ilce/{town_id}/kurum/-1/klinik/{clinic.value}/ana-kurum/select-input"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()["data"]
            return Hospital.flatten(data)
        else:
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_inspection_rooms(self, hospital: Hospital, clinic: Clinic) -> List[InspectionRoom]:
        url = f"https://prd.mhrs.gov.tr/api/kurum/kurum/muayene-yeri/ana-kurum/{hospital.value}/kurum/-1/klinik/{clinic.value}/select-input"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()["data"]
            return [InspectionRoom.from_dict(item) for item in data]
        else:
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_doctors(self, hospital: Hospital, clinic: Clinic) -> List[Doctor]:
        url = f"https://prd.mhrs.gov.tr/api/kurum/hekim/hekim-klinik/hekim-select-input/anakurum/{hospital.value}/kurum/-1/klinik/{clinic.value}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()["data"]
            return [Doctor.from_dict(item) for item in data]
        else:
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_schedules(self, city: City, town: Town | None, clinic: Clinic, hospital: Hospital | None, inspection_room: InspectionRoom | None, doctor: Doctor | None) -> List[Schedule]:
        town_id = -1 if town is None else town.value
        hospital_id = -1 if hospital is None else hospital.value
        inspection_room_id = -1 if inspection_room is None else inspection_room.value
        doctor_id = -1 if doctor is None else doctor.value
        url = "https://prd.mhrs.gov.tr/api/kurum-rss/randevu/slot-sorgulama/arama"
        # TODO cinsiyet parametresini araştır
        payload = {
            "aksiyonId": "200",
            "cinsiyet": "F",
            "ekRandevu": True,
            "mhrsHekimId": doctor_id,
            "mhrsIlId": city.value,
            "mhrsIlceId": town_id,
            "mhrsKlinikId": clinic.value,
            "mhrsKurumId": hospital_id,
            "muayeneYeriId": inspection_room_id,
            "randevuZamaniList": [],
            "tumRandevular": False
        }
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            data = response.json()["data"]
            hospital_schedules = Schedule.list_from_json(data["hastane"])
            polyclinic_schedules = Schedule.list_from_json(data["semt"])
            return hospital_schedules + polyclinic_schedules
        if response.status_code == 404:
            res = response.json()
            if "errors" in res and len(res["errors"]) == 1 and "kodu" in res["errors"][0] and res["errors"][0]["kodu"] == "RND4010":
                """ Hiçbir doktorun randevu cetveli olmadığı durumda boş liste döner """
                return []
        if response.status_code == 428:
            res = response.json()
            """ Sistemin geri bildirim gönderme isteğine onay vermemek bot davranışı olarak değerlendirilebilir. Bu yüzden bu istek bu kodlarla onaylanıyor. """
            if "warnings" in res and len(res["warnings"]) == 1 and "kodu" in res["warnings"][0]:
                if res["warnings"][0]["kodu"] == "RND4030":
                    try:
                        logging.warning("Sistem geri bildirim gönderme isteği yolladı. Onay veriliyor.")
                        time.sleep(0.1)
                        self.ask_schedule_creation(clinic, hospital, inspection_room, doctor)
                        time.sleep(0.1)
                        return self.get_all_schedules(city, town, clinic, hospital, inspection_room, doctor)
                    except Exception as e:
                        logging.exception(e)
                    return []
                elif res["warnings"][0]["kodu"] == "RND4034":
                    try:
                        logging.warning("Sistem aile hekiminden randevu almaya yönlendiriyor.")
                        time.sleep(0.1)
                        self.skip_family_doctor_request()
                        time.sleep(0.1)
                        self.ask_schedule_creation(clinic, hospital, inspection_room, doctor)
                        logging.info("Aile hekimi yönlendirilmesi atlatıldı.")
                        time.sleep(0.1)
                        return self.get_all_schedules(city, town, clinic, hospital, inspection_room, doctor)
                    except Exception as e:
                        logging.exception(e)
        raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def skip_family_doctor_request(self) -> None:
        url = "https://prd.mhrs.gov.tr/api/yonetim/genel/mesaj/by-kodu/GNL2030"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            res = response.json()
            if "infos" in res and len(res["infos"]) == 1 and "kodu" in res["infos"][0] and res["infos"][0]["kodu"] == "GNL2030":
                """ Aile hekimi yönlendirmesinin 2. aşaması (devam et butonuna tıklandıktan sonrası) """
                logging.info("Aile hekimi yönlendirilmesinin atlatılmasının 1. aşaması OK.")
                time.sleep(0.1)
                url = "https://prd.mhrs.gov.tr/api/yonetim/genel/lookup/selectinput/HATIRLATMA_SAAT_SECIMI"
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    logging.info("Aile hekimi yönlendirilmesinin atlatılmasının 2. aşaması OK.")
                else:
                    logging.warning("Sistem aile hekimine yönlendiriyor. Bu yönlendirmenin atlatılması 2. aşamada hata ile karşılaşıyor.")
                    raise RuntimeError(response.status_code, response.json())
        else:
            logging.warning("Sistem aile hekimine yönlendiriyor. Bu yönlendirmenin atlatılması 1. aşamada hata ile karşılaşıyor.")
            raise RuntimeError(response.status_code, response.json())


    @relog_aspect
    def ask_schedule_creation(self, clinic: Clinic, hospital: Hospital | None, inspection_room: InspectionRoom | None, doctor: Doctor | None) -> None:
        """
            Belirlenen kriterlere uygun randevu olmadığında ve daha sonrasında bu kriterlere uygun randevu olduğu zaman
            kullanıcıya bilgi verilmesi için bir fonksiyon ama bu projenin kapsamından çıkıyor, yinede yarım şekilde bırakıyorum
            belki daha sonra farklı şekilde kullanılabilir.
        """
        url = "https://prd.mhrs.gov.tr/api/kurum/randevu-talep"
        doctor_id = doctor.value if doctor is not None else -1
        clinic_id = clinic.value if clinic is not None else -1
        hospital_id = hospital.value if hospital is not None else -1
        inspection_room_id = inspection_room if inspection_room is not None else -1
        payload = {
            "lhatirlatmaSaatSecimi": "1",
            "mhrsHekimId": doctor_id,
            "mhrsKlinikId": clinic_id,
            "mhrsKurumId": hospital_id,
            "muayeneYeriId": inspection_room_id
        }
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            logging.info("Onay verme başarılı.")
        else:
            logging.warning("Onay verme başarısız.")
            raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def get_all_appointments(self, city_id: int, clinic_id: int, hospital_id: int, doctor_id: int) -> List[Appointment]:
        url = "https://prd.mhrs.gov.tr/api/kurum-rss/randevu/slot-sorgulama/slot"
        # TODO cinsiyet parametresini araştır
        payload = {
            "aksiyonId": 200,
            "cinsiyet": "F",
            "ekRandevu": True,
            "mhrsHekimId": doctor_id,
            "mhrsIlId": city_id,
            "mhrsKlinikId": clinic_id,
            "mhrsKurumId": hospital_id,
            "muayeneYeriId": -1,
            "randevuZamaniList": [],
            "tumRandevular": False
        }
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            data = response.json()["data"]
            return Appointment.list_from_response_data(data)
        if response.status_code == 404:
            res = response.json()
            if "errors" in res and len(res["errors"]) == 1 and "kodu" in res["errors"][0] and res["errors"][0]["kodu"] == "RND4010":
                """ Bir doktorun randevu cetvelinin dolması durumunda bu hata dönüyor """
                return []
        raise RuntimeError(response.status_code, response.json())

    @relog_aspect
    def save_appointment(self, appointment: Appointment, appointment_note: str) -> str:
        url = "https://prd.mhrs.gov.tr/api/kurum/randevu/randevu-ekle"
        # TODO yenidoğan parametresini araştır
        payload = {
            "baslangicZamani": appointment.baslangicZamani,
            "bitisZamani": appointment.bitisZamani,
            "fkCetvelId": appointment.fkCetvelId,
            "fkSlotId": appointment.fkSlotId,
            "muayeneYeriId": appointment.muayeneYeriId,
            "randevuNotu": appointment_note,
            "yenidogan": False
        }
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            data = response.json()["data"]
            city = data["kurum"]["ilAdi"]
            town = data["kurum"]["ilceAdi"]
            clinic = data["klinik"]["mhrsKlinikAdi"]
            hospital = data["kurum"]["kurumAdi"]
            doctor = data["hekim"]["ad"] + " " + data["hekim"]["soyad"]
            inspection_room = data["muayeneYeri"]["adi"]
            appointment_date = data["randevuBaslangicZamaniStr"]["gunAyGunIsmi"]
            appointment_hour = data["randevuBaslangicZamaniStr"]["saat"] + " - " + data["randevuBitisZamaniStr"]["saat"]
            res_str = (f"Randevu Kaydı Yapıldı.\nİl: {city}\nİlçe: {town}\nKlinik: {clinic}\nHastane: {hospital}\n"
                       f"Doktor: {doctor}\nMuayene Yeri: {inspection_room}\nRandevu Tarihi: {appointment_date}\n"
                       f"Randevu Saati: {appointment_hour}\nRandevu detaylarını MHRS de inceleyebilirsiniz.")
            return res_str
        raise RuntimeError(response.status_code, response.json())

