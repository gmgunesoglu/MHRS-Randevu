import ntplib
import time

""" 
    Network Time Protocol (NTP)
    Protokol: UDP, port 123 
    1980’lerden beri kullanılan çok eski ve güvenilir bir protokol.
    manuel denemeler için bir main fonksiyonu kuruldu.
"""

class GoogleNtpClient:
    def __init__(self, retries=3, timeout=3):
        self.client = ntplib.NTPClient()
        self.retries = retries
        self.timeout = timeout

    def get_time_offset(self):
        """
            Google zaman sunucusu ile yerel bilgisayar arasındaki gerçek zaman farkını getirir.
        """
        last_exception = None
        for attempt in range(self.retries):
            try:
                """ 
                    t1: istemcinin sorguyu yolladığı zaman.
                    t2: sunucunun sorguyu aldığı zaman.
                    t3: sunucunun cevabı yolladığı zaman.
                    t4: cevabın istemciye ulaştığı zaman.
                    delay: networkdeki zaman kaybı
                    offset: istemci ile sunucu arasındaki zaman farklı (delay işlenmemiş)
                """

                """ ntp nasıl çalışır manuel izleme/test için """
                # t1 = time.time()
                # response = self.client.request("time.google.com", version=3, timeout=self.timeout)
                # t4 = time.time()
                # t2 = response.recv_time
                # t3 = response.tx_time
                # delay = (t4 - t1) - (t3 - t2)
                # offset = ((t2 - t1) + (t3 - t4)) / 2

                # print(f"t1: {t1}")
                # print(f"t2: {t2:.16f}")
                # print(f"t3: {t3:.16f}")
                # print(f"t4: {t4}")
                # print(f"response.offset: {response.offset:.6f}")
                # print(f"response.delay: {response.delay:.6f}")
                # return offset, delay

                """ ntp nin değerleri arada 0.001 saniyelik farkla daha doğru """
                response = self.client.request("time.google.com", version=3, timeout=self.timeout)
                return response.offset, response.delay
            except Exception as e:
                last_exception = e
                time.sleep(5)
        raise RuntimeError(f"{last_exception}")


if __name__ == "__main__":
    client = GoogleNtpClient()
    try:
        offset, delay = client.get_time_offset()
        print(f"Sunucu ile istemci saat farkı: {offset:.6f} sn")
        print(f"Ağ gecikmesi: {delay:.6f} sn")
    except RuntimeError as e:
        print("Hata:", e)
