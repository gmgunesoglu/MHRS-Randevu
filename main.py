import datetime
import tkinter as tk
from tkinter import messagebox
from mhrs_client import MHRSClient
from google_ntp_client import GoogleNtpClient
import config
from datetime import date, timedelta
import threading
import time
import logging
from model import *


BLUE = "\033[94m"
RESET = "\033[0m"

logging.basicConfig(
    level=logging.INFO,
    format=BLUE + "%(asctime)s %(levelname)s: %(message)s" + RESET,
    datefmt="%Y-%m-%d %H:%M:%S"
)

selected_city: City
selected_town: Town
selected_clinic: Clinic
selected_hospital: Hospital
selected_inspection_room: InspectionRoom
selected_doctor: Doctor


class AutoCompleteCombo:
    last_selected = False
    enabled = True
    selected_index = None
    def __init__(self, root, options, placeholder: str, on_select_callback, on_deselect_callback, enabled=True):
        self.root = root
        self.options = [turkish_normalize(opt) for opt in options]
        self.filtered = self.options.copy()
        self.placeholder = placeholder
        self.on_select_callback = on_select_callback
        self.on_deselect_callback = on_deselect_callback

        # Entry (arama kutusu)
        self.search = tk.Entry(root, width=50, fg="grey")
        self.search.pack(pady=5)
        self.search.bind("<FocusIn>", self.search_selected)
        self.search.bind("<FocusOut>", self.search_deselect)
        self.search.bind("<KeyRelease>", self.on_keyrelease)
        # self.search.bind("<Button-1>", self.search_selected)
        self.search.insert(0, self.placeholder)

        # Listbox
        self.listbox = tk.Listbox(root, width=50, height=6)
        self.listbox.bind("<ButtonRelease-1>", self.on_select)
        # self.listbox.bind("<<ListboxSelect>>", self.on_select)
        for item in self.options:
            self.listbox.insert(tk.END, item)

        self.enabled = enabled
        if not enabled:
            self.enabled = False
            self.search.config(state="disabled")


    def set_enable(self, options):
        """
            instance ı kullanabilir hale getitirir
        """
        self.enabled = True
        self.search.config(state="normal")
        self.options = [turkish_normalize(opt) for opt in options]
        self.filtered = self.options.copy()
        self.listbox.delete(0, tk.END)
        for item in self.options:
            self.listbox.insert(tk.END, item)

    def set_disable(self):
        """ search entery seçilemez hale gelir. """
        if self.enabled:
            self.enabled = False
            self.selected_index = None
            self.__reset()
            self.search.config(state="disabled")
            self.on_deselect_callback()

    def __reset(self):
        """ seach entery içeriği siler, placeholder yerleştirilir """
        self.search.delete(0, tk.END)
        self.search.insert(0, self.placeholder)
        self.search.config(fg="grey")

    def search_selected(self, event):
        """ Placeholder varsa temizle """
        self.last_selected = True
        if self.search.get() == self.placeholder and self.search.cget("fg") == "grey":
            self.search.delete(0, tk.END)
            self.search.config(fg="black")
        self.show_listbox()

    def search_deselect(self, event=None):
        """
            Açık olan bir alan kapatıldığında farklı durumlar mevcut:
                1- toolbar kapatılır ve last_selected false olur.
                2- Eğer search entry boş ise veya yarım dolu (eşleşmeyen bir string) ise resetlenir.
                3- Eğer daha önce eşleşmiş bir string var ise eşleşmeyi kaldırır ve roota geri çağrı yapar.
        """
        widget_in_focus = self.root.focus_get()
        if widget_in_focus == self.listbox:
            self.search.master.focus_set()
            return

        self.last_selected = False
        if self.search.get() not in self.options:
            self.__reset()
            self.listbox.place_forget()
            self.filtered = self.options.copy()
            if self.selected_index is not None:
                self.selected_index = None
                self.on_deselect_callback()
        elif widget_in_focus != self.listbox:
            self.listbox.place_forget()
        self.search.master.focus_set()

    def show_listbox(self, event=None):
        """Listeyi göster"""
        self.listbox.place(x=self.search.winfo_x(), y=self.search.winfo_y() + self.search.winfo_height())
        self.listbox.lift()

    def hide_listbox(self):
        """Listeyi gizle"""
        self.listbox.place_forget()

    def update_listbox(self):
        """Entry içindeki yazıya göre listeyi güncelle"""
        typed = turkish_normalize(self.search.get())
        if typed is None:
            typed = ""
        self.filtered = [opt for opt in self.options if opt.startswith(typed)]
        self.listbox.delete(0, tk.END)

        if self.filtered:
            for item in self.filtered:
                self.listbox.insert(tk.END, item)
            self.show_listbox()
        else:
            self.hide_listbox()

    def on_keyrelease(self, event):
        """Yazı yazıldıkça filtreleme"""
        if self.search.cget("fg") == "grey":
            return  # placeholder varken filtreleme yapma
        self.update_listbox()

    def on_select(self, event):
        """Listeden seçilince Entry’ye yaz (index güvenli şekilde)"""
        selection = self.listbox.curselection()
        if not selection:
            return

        # Listbox’tan seçilen satırın indexi
        local_index = selection[0]
        try:
            value = self.filtered[local_index]
        except Exception as e:
            logging.exception(f"{e}")
            return

        # Entry’ye yaz
        self.search.delete(0, tk.END)
        self.search.insert(0, value)
        self.search.config(fg="black")
        self.hide_listbox()

        # Global indexi bul (filtered -> options mapping)
        global_index = self.options.index(value)

        # Callback çağır
        if self.selected_index is None or self.selected_index != global_index:
            self.selected_index = global_index
            self.on_select_callback(global_index)
        self.search.master.focus_set()
        self.last_selected = False


class FirstWindow:
    ph_username = "T.C. Kimlik No"
    ph_password = "Parola"
    time_synchronization_finished = False

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MHRS-Randevu")
        self.root.geometry(get_screen_locate(self.root, 250, 200))
        self.root.resizable(False, False)

        """ Boş alan """
        free_frame = tk.Frame(self.root)
        free_frame.pack(pady=10)

        if config.user_agent == "Kendi user-agent bilgini buraya yaz.":
            messagebox.showerror("Hata", "Lütfen kurulum talimatlarını tekrar okuyun ve \"mhrs_data.json\" dosyası kendi user-agent bilginiz ile üncelleyin")

        vcmd = (self.root.register(self.validate_tc), "%P")
        self.username_entry = tk.Entry(self.root, fg="gray", width=22, validate="key", validatecommand=vcmd)
        self.username_entry.insert(0, self.ph_username)
        self.username_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(self.username_entry, self.ph_username))
        self.username_entry.bind("<FocusOut>", lambda e: self.add_placeholder(self.username_entry, self.ph_username))
        self.username_entry.bind("<KeyRelease>", lambda e: self.check_login_btn())
        self.username_entry.pack(pady=10)

        self.password_entry = tk.Entry(self.root, fg="gray", width=22)
        self.password_entry.insert(0, self.ph_password)
        self.password_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(self.password_entry, self.ph_password, is_password=True))
        self.password_entry.bind("<FocusOut>", lambda e: self.add_placeholder(self.password_entry, self.ph_password, is_password=True))
        self.password_entry.bind("<KeyRelease>", lambda e: self.check_login_btn())
        self.password_entry.pack(pady=10)

        # Login Button
        self.login_btn = tk.Button(self.root, text="Giriş", command=self.login, width=18, state="disabled")
        self.login_btn.pack(pady=10)

        # zaman senkronizasyonu
        self.lbl_time_synchronization = tk.Label(self.root, text="Zaman senkronizasyonu\nbaşlatıldı...", font=("Arial", 10))
        self.lbl_time_synchronization.pack(pady=10)
        threading.Thread(target=self.update_time_offset, daemon=True).start()

        self.root.mainloop()

    def update_time_offset(self):
        """ time_offset'in güncellenmesi """
        global time_offset
        try:
            time_offset, network_delay = google_ntp_client.get_time_offset()
            self.lbl_time_synchronization.config(
                text="Zaman senkronizasyonu\nyapıldı."
            )
        except Exception as e:
            message = ("Yerel bilgisayarınızın saati ile global saat arasındaki fark hesaplanırken bir hata oluştu. "
                       "Eğer bilgisayarınızın saatinin güncel olduğundan ve internet bağlantınızın aktif olduğundan "
                       "eminseniz devam edebilirsiniz. Hata detayları:", e)
            messagebox.showerror("Hata", f"{message}")
            logging.exception(e)
            self.lbl_time_synchronization.config(
                text="Zaman senkronizasyonu\nyapılamadı."
            )
        self.time_synchronization_finished = True
        self.check_login_btn()

    def validate_tc(self, new_value):
        """Sadece rakam ve max 11 karakter kabul et, placeholder'a izin ver"""
        if new_value == self.ph_username:
            return True
        if new_value.isdigit() or new_value == "":
            return len(new_value) <= 11
        return False

    def clear_placeholder(self, entry, placeholder, is_password=False):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg="black")
            if is_password:
                entry.config(show="*")

    def add_placeholder(self, entry, placeholder, is_password=False):
        if not entry.get():
            entry.insert(0, placeholder)
            entry.config(fg="gray")
            if is_password:
                entry.config(show="")

    def check_login_btn(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if self.time_synchronization_finished and username.isdigit() and len(username) == 11 and len(password) >= 8 and password != "Şifre giriniz:":
            self.login_btn.config(state="normal")
        else:
            self.login_btn.config(state="disabled")

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        try:
            mhrs_client.login(username, password)
            self.root.destroy()
            SecondWindow()
        except Exception as e:
            messagebox.showerror("Hata", f"{e}")
            logging.exception(e)


class SecondWindow:
    selected_city = None
    towns = None
    selected_town = None
    clinics = None
    selected_clinic = None
    hospitals = None
    selected_hospital = None
    doctors = None
    selected_doctor = None
    inspection_rooms = None
    selected_inspection_room = None
    combos = []

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MHRS-Randevu")
        self.root.geometry(get_screen_locate(self.root, 400, 300))
        self.root.resizable(False, False)

        self.root.bind("<Button-1>", self.on_root_click)

        try:
            self.cities = mhrs_client.get_all_cities()
        except Exception as e:
            messagebox.showerror("Hata", f"{e}")
            logging.exception(e)

        """ Boş alan """
        free_frame = tk.Frame(self.root)
        free_frame.pack(pady=10)

        self.combo_city = AutoCompleteCombo(self.root, [c.text for c in self.cities], "Şehir seçiniz:", on_select_callback=self.city_selected, on_deselect_callback=self.clear_city)
        self.combos.append(self.combo_city)

        self.combo_town = AutoCompleteCombo(self.root, [], "İlçe seçiniz:", on_select_callback=self.town_selected, on_deselect_callback=self.clear_town, enabled=False)
        self.combos.append(self.combo_town)

        self.combo_clinic = AutoCompleteCombo(self.root, [], "Klinik seçiniz:", on_select_callback=self.clinic_selected, on_deselect_callback=self.clear_clinic, enabled=False)
        self.combos.append(self.combo_clinic)

        self.combo_hospital = AutoCompleteCombo(self.root, [], "Hastane seçiniz:", on_select_callback=self.hospital_selected, on_deselect_callback=self.clear_hospital, enabled=False)
        self.combos.append(self.combo_hospital)

        self.combo_inspection_room = AutoCompleteCombo(self.root, [], "Muayene yeri seçiniz:", on_select_callback=self.inspection_room_selected, on_deselect_callback=self.clear_inspection_room, enabled=False)
        self.combos.append(self.combo_inspection_room)

        self.combo_doctor = AutoCompleteCombo(self.root, [], "Hekim seçiniz:", on_select_callback=self.doctor_selected, on_deselect_callback=self.clear_doctor, enabled=False)
        self.combos.append(self.combo_doctor)

        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(pady=10)

        self.btn_go_back = tk.Button(frame_buttons, text="Geri", command=self.go_back_window, width=20)
        self.btn_go_back.pack(side="left", padx=5)

        self.btn_go_next = tk.Button(frame_buttons, text="İleri", command=self.go_next_window, width=20, state="disabled")
        self.btn_go_next.pack(side="left", padx=5)

        self.root.mainloop()

    def on_root_click(self, event):
        """
            bu pencere üzerindeki tıklamaları dinler,
            seçili/açık alan(combo) varsa ve yapılan
            tıklama onun üzerinde değilse o alanı kapatır.
        """
        for combo in self.combos:
            if combo.last_selected:
                if event.widget not in (combo.search, combo.listbox):
                    combo.search_deselect(event)

    def go_back_window(self):
        self.root.destroy()
        FirstWindow()

    def go_next_window(self):
        try:
            mhrs_client.get_all_schedules(
                self.selected_city, self.selected_town, self.selected_clinic,
                self.selected_hospital, self.selected_inspection_room, self.selected_doctor
            )
        except Exception as e:
            messagebox.showerror("Hata", f"{e}")
            logging.exception(e)
            return
        global selected_city
        selected_city = self.selected_city
        global selected_town
        selected_town = self.selected_town
        global selected_clinic
        selected_clinic = self.selected_clinic
        global selected_hospital
        selected_hospital = self.selected_hospital
        global selected_inspection_room
        selected_inspection_room = self.selected_inspection_room
        global selected_doctor
        selected_doctor = self.selected_doctor
        self.root.destroy()
        ThirdWindow()

    def clear_city(self):
        """
            Şehir seçimi kaldırıldığında:
            ilçe ve klinik seçimleri kaldırılır ve bu alanlar pasif edilir.
            Bu işlem zincirleme olarak alt alanlara ilerler.
        """
        self.selected_city = None
        self.combo_clinic.set_disable()
        self.combo_town.set_disable()


    def city_selected(self, index):
        """
            Şehir seçildikten sonra hem ilçe hemde klinik seçilebilir olur.
            Seçilen şehir değiştirildiğinde, bu alanlar resetlenir.
        """
        if self.selected_city is not None:
            self.clear_city()
        self.selected_city = self.cities[index]
        try:
            """ ilçe işlemleri... """
            self.towns = mhrs_client.get_all_towns(self.selected_city)
            self.combo_town.set_enable([t.text for t in self.towns])
            """ klinik işlemleri... """
            self.clinics = mhrs_client.get_all_clinics(self.selected_city, None)
            self.combo_clinic.set_enable([c.text for c in self.clinics])
        except Exception as e:
            messagebox.showerror("Hata", f"{e}")
            logging.exception(e)


    def clear_town(self):
        """
            ilçe seçimi kaldırıldığında 3 durum ile karşılaşılabilir:
            1- seçili bir il yok (il seçiminin kaldırılmasıyla çağığırlmış).
                clear_clinic daha önce çalıştığı için zincirleme işlem burada son bulacaktır.
            2- seçili il var
                zincirleme işlem burada başlatılır, klinik alanı tekrar aktif edilir

        """
        if self.selected_town is None:
            return
        self.selected_town = None
        if self.selected_city is not None:
            self.combo_clinic.set_disable()
            try:
                self.clinics = mhrs_client.get_all_clinics(self.selected_city, None)
                self.combo_clinic.set_enable([c.text for c in self.clinics])
            except Exception as e:
                messagebox.showerror("Hata", f"{e}")
                logging.exception(e)
            return


    def town_selected(self, index):
        """
            İlçe seçildikten sonra klinikler il ve ilçeye göre filtrelenir ve yenilenir.
        """
        if self.selected_clinic is not None:
            self.combo_clinic.set_disable()
        self.selected_town = self.towns[index]
        try:
            self.clinics = mhrs_client.get_all_clinics(self.selected_city, self.selected_town)
            self.combo_clinic.set_enable([c.text for c in self.clinics])
        except Exception as e:
            messagebox.showerror("Hata", f"{e}")
            logging.exception(e)

    def clear_clinic(self):
        if self.selected_clinic is None:
            return
        self.selected_clinic = None
        self.btn_go_next.config(state="disabled")
        self.combo_hospital.set_disable()

    def clinic_selected(self, index):
        """
            kilinik seçildikten sonra hastaneler seçilebilir olur.
            Bu aşamadan sonraki aşamaalar randevu arama için opsiyoneldir,
            arana sonuçlarını daraltır/filtreler.
        """
        if self.selected_clinic is not None:
            self.combo_hospital.set_disable()
        self.btn_go_next.config(state="normal")
        self.selected_clinic = self.clinics[index]
        try:
            self.hospitals = mhrs_client.get_all_hospitals(self.selected_city, self.selected_town, self.selected_clinic)
            self.combo_hospital.set_enable([h.text for h in self.hospitals])
        except Exception as e:
            messagebox.showerror("Hata", f"{e}")
            logging.exception(e)

    def clear_hospital(self):
        if self.selected_hospital is None:
            return
        self.selected_hospital = None
        self.combo_inspection_room.set_disable()
        self.combo_doctor.set_disable()

    def hospital_selected(self, index):
        """
            Hastane seçildikten sonra muayne yerleri ve doktorlar seçilebilir (Opsiyonel).
        """
        self.selected_hospital = self.hospitals[index]
        try:
            self.inspection_rooms = mhrs_client.get_all_inspection_rooms(self.selected_hospital, self.selected_clinic)
            self.combo_inspection_room.set_enable([ir.text for ir in self.inspection_rooms])
            self.doctors = mhrs_client.get_all_doctors(self.selected_hospital, self.selected_clinic)
            self.combo_doctor.set_enable([d.text for d in self.doctors])
        except Exception as e:
            messagebox.showerror("Hata", f"{e}")
            logging.exception(e)

    def clear_inspection_room(self):
        self.selected_inspection_room = None

    def inspection_room_selected(self, index):
        """
            Sadece muayene yeri seçilmiş olur. Randevu arama sonuçları daralır.
        """
        self.selected_inspection_room = self.inspection_rooms[index]

    def clear_doctor(self):
        self.selected_doctor = None
    def doctor_selected(self, index):
        """
            Sadece doktor seçilmiş olur. Randevu arama sonuçları daralır.
        """
        self.selected_doctor = self.doctors[index]


class ThirdWindow:
    next_15_days = None

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MHRS-Randevu")
        self.root.geometry(get_screen_locate(self.root, 500, 620))
        self.root.resizable(False, False)

        tk.Label(self.root, text="Sizin için uygun olan günleri\nsıralı şekilde seçiniz.", font=("Arial", 14)).pack(pady=10)

        # 15 günü hazırla
        self.get_next_15_days()

        # Kullanıcının seçtiği günler (sıra ile)
        self.selected_days = []

        # Tarihleri gösterecek frame
        frame_days = tk.Frame(self.root)
        frame_days.pack(pady=10)

        # Checkbutton’lar için değişkenler
        self.vars = {}

        for day in self.next_15_days:
            text = turkish_date_str(day)

            var = tk.IntVar()
            cb = tk.Checkbutton(
                frame_days,
                text=text,
                variable=var,
                command=lambda d=day, v=var: self.on_day_toggle(d, v),
                font=("Arial", 10)
            )
            cb.pack(anchor="w")
            self.vars[day] = var

        # Butonlar
        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(pady=10)

        self.btn_go_back = tk.Button(frame_buttons, text="Geri", command=self.go_back_window, width=20)
        self.btn_go_back.pack(side="left", padx=5)

        self.btn_go_next = tk.Button(frame_buttons, text="İleri", command=self.go_next_window, width=20, state="disabled")
        self.btn_go_next.pack(side="left", padx=5)

        # Seçilen günleri gösteren label
        self.message_selected = tk.Message(self.root, text="Seçimleriniz: []", width=350, font=("Arial", 8))
        self.message_selected.pack(pady=10)

        self.root.mainloop()

    def go_back_window(self):
        self.root.destroy()
        SecondWindow()

    def go_next_window(self):
        self.root.destroy()
        FourthWindow(self.selected_days)

    def get_next_15_days(self):
        day = date.today()
        self.next_15_days = []
        while len(self.next_15_days) < 15:
            if day.weekday() < 5:
                self.next_15_days.append(day)
            day += timedelta(days=1)

    def on_day_toggle(self, day, var):
        if var.get() == 1:
            if day not in self.selected_days:
                self.selected_days.append(day)
        else:
            if day in self.selected_days:
                self.selected_days.remove(day)
        self.message_selected.config(
            text="Seçimleriniz sırasıyla: " + ", ".join(turkish_date_str(d) for d in self.selected_days)
        )

        # Placeholder değilse ve uzunluklar uygunsa aktif et
        if len(self.selected_days) > 0:
            self.btn_go_next.config(state="normal")
        else:
            self.btn_go_next.config(state="disabled")


        # print("Seçilen günler:")
        # for day in self.selected_days:
        #     print(day.strftime("%Y-%m-%d"))


class FourthWindow:
    hours_list = ["08:00", "09:00", "10:00", "11:00", "12:00",
                  "14:00", "15:00", "16:00", "17:00", "18:00"]

    def __init__(self, selected_days):
        self.root = tk.Tk()
        self.root.title("MHRS-Randevu")
        self.root.geometry(get_screen_locate(self.root, 400, 500))
        self.root.resizable(False, False)
        self.selected_days = selected_days
        self.root.resizable(False, False)

        tk.Label(self.root, text="Sizin için uygun olan saatleri\nsıralı şekilde seçiniz.", font=("Arial", 14)).pack(pady=10)

        self.selected_hours = []
        frame_hours = tk.Frame(self.root)
        frame_hours.pack(pady=10)
        self.vars = {}
        for hour in self.hours_list:
            var = tk.IntVar()
            cb = tk.Checkbutton(
                frame_hours,
                text=hour,
                variable=var,
                command=lambda h=hour, v=var: self.on_hour_toggle(h, v),
                font=("Arial", 10)
            )
            cb.pack(anchor="w")
            self.vars[hour] = var

        # Butonlar
        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(pady=10)

        self.btn_go_back = tk.Button(frame_buttons, text="Geri", command=self.go_back_window, width=20)
        self.btn_go_back.pack(side="left", padx=5)

        self.btn_go_next = tk.Button(frame_buttons, text="İleri", command=self.go_next_window, width=20, state="disabled")
        self.btn_go_next.pack(side="left", padx=5)

        # Seçilen saatleri gösteren label
        self.message_selected = tk.Message(self.root, text="Seçimleriniz: []", width=350, font=("Arial", 8))
        self.message_selected.pack(pady=10)

        self.root.mainloop()

    def go_back_window(self):
        self.root.destroy()
        ThirdWindow()

    def go_next_window(self):
        self.root.destroy()
        FifthWindow(self.selected_days, self.selected_hours)

    def on_hour_toggle(self, hour, var):
        """Checkbutton işaretlenince/kaldırılınca çalışır"""
        if var.get() == 1:
            if hour not in self.selected_hours:
                self.selected_hours.append(hour)
        else:
            if hour in self.selected_hours:
                self.selected_hours.remove(hour)

        # Güncel seçimi ekrana yaz
        self.message_selected.config(
            text="Seçimleriniz sırasıyla: " + ", ".join(self.selected_hours)
        )
        print("Seçilen saatler:", self.selected_hours)
        if len(self.selected_hours) > 0:
            self.btn_go_next.config(state="normal")
        else:
            self.btn_go_next.config(state="disabled")


class FifthWindow:
    def __init__(self, selected_days, selected_hours):

        self.root = tk.Tk()
        self.root.title("MHRS-Randevu")
        self.root.geometry(get_screen_locate(self.root, 400, 300))
        self.root.resizable(False, False)

        """ Boş alan """
        free_frame = tk.Frame(self.root)
        free_frame.pack(pady=10)

        self.entry_appointment_message = tk.Entry(self.root, fg="gray", width=30)
        self.entry_appointment_message.insert(0, "Randevu notu ekleyebilirsiniz:")
        self.entry_appointment_message.bind("<FocusIn>", lambda e: self.clear_placeholder("Randevu notu ekleyebilirsiniz:"))
        self.entry_appointment_message.bind("<FocusOut>", lambda e: self.add_placeholder("Randevu notu ekleyebilirsiniz:"))
        self.entry_appointment_message.pack(pady=10)

        """ Yakalanan randevular kullanıcının kriterlerine göre filtrelenip sıralanacaktır. """
        """ Python 3.7 den itibaren sözlükler sıralamayı korur ama garantilemek için liste kullanıldı. """
        self.day_hour_dict = {}
        self.day_hour_list = []
        for dd in selected_days:
            d = dd.strftime("%d.%m.%Y")
            for h in selected_hours:
                self.day_hour_list.append(f'{d} {h}')
                self.day_hour_dict[f'{d} {h}'] = []

        self.lbl_searching = tk.Label(self.root, text="Randevu aramayı başlatabilirsiniz.", font=("Arial", 12))
        self.lbl_searching.pack(pady=10)

        self.lbl_schedule = tk.Label(self.root, text="", font=("Arial", 11))
        self.lbl_schedule.pack(pady=10)

        self.lbl_appointment = tk.Label(self.root, text="", font=("Arial", 11))
        self.lbl_appointment.pack(pady=10)

        # Butonlar
        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(pady=20)

        self.btn_go_back = tk.Button(frame_buttons, text="Geri", command=self.go_back_window, width=20)
        self.btn_go_back.pack(side="left", padx=5)

        self.btn_go_next = tk.Button(frame_buttons, text="Başlat", command=self.start_search_thread, width=20)
        self.btn_go_next.pack(side="left", padx=5)

        # Thread kontrolü için flag
        self.search_running = False
        self.search_thread = None

        self.root.mainloop()

    def go_back_window(self):
        self.root.destroy()
        FourthWindow([])

    def start_search_thread(self):
        # 1. Başlat butonunu pasif yap
        self.lbl_searching.config(text="Randevu aranıyor...")
        self.btn_go_next.config(state="disabled")

        # 2. Geri butonunun text ve fonksiyonunu değiştir
        self.btn_go_back.config(text="Aramayı Durdur", command=self.stop_search)

        # 3. Thread başlat
        self.search_running = True
        self.search_thread = threading.Thread(target=self.start_search, daemon=True)
        self.search_thread.start()

    def start_search(self):
        """
            schedule = bir doktorun randevu cetveli olmak üzere...
            schedules çekilir ve her bir saniyede bir schedule üzerinden randevular (appointment) çekilir.
            Çekilen randevular, kullanıcı kriterlerine göre işlenir. (filtreleme ve önceliklendirme)
            En az bir uygun randevu bulunana kadar, randevu döngüsü 10 kez döner,
            randevu döngüsünden sonra tekrar schedule döngüsü çalışır, program sonlandırılana kadar!
        """
        schedule_request_count = 1
        next_request_ts = get_next_request_ts()
        while self.search_running:
            """ Doktor randevu slotlarının saatin 5 er dakikalık dilimlerinde çekilmesi için bekleme döngüsü """
            while self.search_running:
                time_dif = next_request_ts - time.time()
                if time_dif <= -0.6:
                    break
                time.sleep(max(time_dif * 0.8, 0.4))
            try:
                schedules_request_time = time.time()
                schedules = mhrs_client.get_all_schedules(
                    selected_city, selected_town, selected_clinic, selected_hospital, selected_inspection_room, selected_doctor
                )
                schedules_request_time = (time.time() + schedules_request_time) / 2 + time_offset
                print(f"schedule_request_count: {schedule_request_count}, current_time: {datetime.datetime.fromtimestamp(schedules_request_time)}")
                schedule_request_count += 1
            except Exception as e:
                messagebox.showerror("Hata", f"{e}")
                logging.exception(e)
                self.root.destroy()
                return
            self.lbl_schedule.config(text=f"Randevu cetveli kontrol edilecek doktor sayısı: {len(schedules)}")
            time.sleep(1)
            next_request_ts = get_next_request_ts()
            if len(schedules) > 0:
                while next_request_ts - time.time() > 30:
                    suitable_appointment_count = 0
                    """ bütün doktor randevu cetvellerindeki randevuları çeker, kullanıcı kriterlerine uygun olanları self.day_hour_dict e ekler. """
                    for i, schedule in enumerate(schedules):
                        try:
                            appointments = mhrs_client.get_all_appointments(selected_city.value, schedule.mhrsKlinikId, schedule.mhrsKurumId, schedule.mhrsHekimId)
                        except Exception as e:
                            messagebox.showerror("Hata", f"{e}")
                            logging.exception(e)
                            return
                        self.lbl_appointment.config(text=f"{i+1}.Doktordan kontrol edilecek randevu sayısı: {len(appointments)}")
                        for appointment in appointments:
                            if appointment.zaman in self.day_hour_dict:
                                self.day_hour_dict[appointment.zaman].append(appointment)
                                suitable_appointment_count += 1
                    """ eğer en az 1 uygun randevu var ise, kullanıcı kriterleri öncelikli olacak şekilde randevu alır. """
                    if suitable_appointment_count > 0:
                        for dh in self.day_hour_list:
                            if len(self.day_hour_dict[dh]) > 0:
                                for appointment in self.day_hour_dict[dh]:
                                    try:
                                        res = mhrs_client.save_appointment(appointment, self.entry_appointment_message.get())
                                        logging.info("Randevu kaydı yapıldı.")
                                        self.root.after(0, lambda: [
                                            messagebox.showinfo("Randevu kaydedildi", f"{res}"),
                                            self.root.destroy()
                                        ])
                                        return
                                    except Exception as e:
                                        logging.exception(e)
                    """ Program akışı bu noktaya geldiyse, uygun görülen tüm randevular denenmiş ama alınamamış demektir. """
                    """ self.day_hour_dict i resetle. """
                    for item in self.day_hour_dict.values():
                        item.clear()
                    time.sleep(5)

    def stop_search(self):
        self.search_running = False
        self.btn_go_back.config(state="normal", text="Geri", command=self.go_back_window)
        self.lbl_searching.config(text="Randevu aramayı başlatabilirsiniz.")

    def clear_placeholder(self, placeholder):
        if self.entry_appointment_message.get() == placeholder:
            self.entry_appointment_message.delete(0, tk.END)
            self.entry_appointment_message.config(fg="black")

    def add_placeholder(self, placeholder):
        if not self.entry_appointment_message.get():
            self.entry_appointment_message.insert(0, placeholder)
            self.entry_appointment_message.config(fg="gray")


def get_screen_locate(root, window_width: int, window_height: int):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int((screen_width / 2) - (window_width / 2))
    y = int((screen_height / 2) - (window_height / 2))
    return f"{window_width}x{window_height}+{x}+{y}"


def turkish_date_str(day: date) -> str:
    return f"{day.strftime("%d")} {config.month_map[day.strftime("%B")]} {config.day_map[day.strftime("%A")]}"


def turkish_normalize(s: str) -> str:
    return s.translate(config.turkish_character_mapping).lower()


def get_next_request_ts():
    current_ts = datetime.datetime.now().timestamp() + time_offset
    return current_ts - current_ts % 300 + 300 - time_offset


if __name__ == "__main__":
    mhrs_client = MHRSClient(config.mhrs_headers)
    google_ntp_client = GoogleNtpClient()
    """ gerçek time_delay değeri, eğer hata olursa message_box ile yazdırmak için ilk pencerede hesaplanır. """
    time_offset = 0
    FirstWindow()
