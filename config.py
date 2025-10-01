import json

with open("mhrs_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    user_agent = data["User-Agent"]
    print(user_agent)

mhrs_headers = {
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Host": "prd.mhrs.gov.tr",
    "Origin": "https://mhrs.gov.tr",
    "Referer": "https://mhrs.gov.tr/",
    "User-Agent": user_agent
}

turkish_character_mapping = str.maketrans({
    "İ": "i",
    "I": "ı",
    "ı": "ı",
    "i": "i",
    "Ğ": "ğ",
    "Ü": "ü",
    "Ş": "ş",
    "Ö": "ö",
    "Ç": "ç",
})

month_map = {
    "January": "Ocak",
    "February": "Şubat",
    "March": "Mart",
    "April": "Nisan",
    "May": "Mayıs",
    "June": "Haziran",
    "July": "Temmuz",
    "August": "Ağustos",
    "September": "Eylül",
    "October": "Ekim",
    "November": "Kasım",
    "December": "Aralık"
}

day_map = {
    "Monday": "Pazartesi",
    "Tuesday": "Salı",
    "Wednesday": "Çarşamba",
    "Thursday": "Perşembe",
    "Friday": "Cuma",
    "Saturday": "Cumartesi",
    "Sunday": "Pazar"
}


