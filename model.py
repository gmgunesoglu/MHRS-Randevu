from dataclasses import dataclass, field
from typing import List

@dataclass
class DropdownListItem:
    value: int
    text: str

@dataclass
class SmallDropdownListItem(DropdownListItem):
    pass

    @classmethod
    def from_dict(cls, data: dict) -> "SmallDropdownListItem":
        return cls(
            value=data["value"],
            text=data["text"]
        )

@dataclass
class BigDropdownListItem(DropdownListItem):
    children: List["BigDropdownListItem"] = field(default_factory=list)
    value2: int = None
    value3: int = None
    text2: str = ""
    favori: bool = False

    @staticmethod
    def from_dict(data: dict) -> "BigDropdownListItem":
        children = [BigDropdownListItem.from_dict(child) for child in data.get("children", [])]
        return BigDropdownListItem(
            value=data["value"],
            text=data["text"],
            children=children,
            value2=data.get("value2"),
            value3=data.get("value3"),
            text2=data.get("text2", ""),
            favori=data.get("favori", False),
        )

    @staticmethod
    def flatten(data: List[dict]) -> List["BigDropdownListItem"]:
        """JSON listesinden düz City listesi döndürür (children dahil)."""
        all_items = []
        seen = set()

        def _walk(node: dict):
            dropdown_item = BigDropdownListItem.from_dict({**node, "children": []})  # çocukları boşalt
            if dropdown_item.value not in seen:
                all_items.append(dropdown_item)
                seen.add(dropdown_item.value)
            for child in node.get("children", []):
                _walk(child)

        for item in data:
            _walk(item)

        return all_items

@dataclass
class City(BigDropdownListItem):
    pass

@dataclass
class Town(SmallDropdownListItem):
    pass

@dataclass
class Clinic(BigDropdownListItem):
    pass

@dataclass
class Hospital(BigDropdownListItem):
    pass

@dataclass
class Doctor(BigDropdownListItem):
    pass

@dataclass
class InspectionRoom(SmallDropdownListItem):
    pass

@dataclass
class Schedule:
    mhrsHekimId: int
    mhrsKlinikId: int
    mhrsKurumId: int
    muayeneYeriId: int

    @classmethod
    def from_json(cls, data: dict) -> "Schedule":
        """Tek JSON objesini ScheduleSlot nesnesine dönüştürür."""
        return cls(
            mhrsHekimId=data["hekim"]["mhrsHekimId"],
            mhrsKlinikId=data["klinik"]["mhrsKlinikId"],
            mhrsKurumId=data["kurum"]["mhrsKurumId"],
            muayeneYeriId=data["muayeneYeri"]["id"],
        )

    @classmethod
    def list_from_json(cls, json_list: List[dict]) -> List["Schedule"]:
        """JSON listesi içinden ScheduleSlot nesne listesi döner."""
        return [cls.from_json(item) for item in json_list]

@dataclass
class Appointment:
    fkSlotId: int
    fkCetvelId: int
    baslangicZamani: str
    bitisZamani: str
    zaman: str
    muayeneYeriId: int

    @classmethod
    def from_slot(cls, slot: dict) -> "Appointment | None":
        """Tek bir slot dict'inden dataclass oluşturur; bos!=True ise None döner."""
        if not slot.get("bos", False):
            return None
        return cls(
            fkSlotId=slot.get("id"),
            fkCetvelId=slot.get("fkCetvelId"),
            baslangicZamani=slot.get("baslangicZamani"),
            bitisZamani=slot.get("bitisZamani"),
            zaman=slot.get("baslangicZamanStr", {}).get("zaman", ""),
            muayeneYeriId=slot.get("slot", {}).get("muayeneYeriId"),
        )

    @classmethod
    def get_appointment_list_from_doctor_schedule_slot(cls, doctor_schedule_slot: List[dict]) -> List["Appointment"]:
        """hekimSlotList yapısını işleyip Appointment listesi döner."""
        results: List[Appointment] = []
        for hekim in doctor_schedule_slot:
            for muayene in hekim.get("muayeneYeriSlotList", []):
                for saat in muayene.get("saatSlotList", []):
                    for slot in saat.get("slotList", []):
                        appt = cls.from_slot(slot)
                        if appt:
                            results.append(appt)
        return results

    @classmethod
    def list_from_response_data(cls, response_data) -> List["Appointment"]:
        """
        response.json()['data'] olarak alınan yapıyı işleyen üst seviye fonksiyon.
        response_data ya bir liste (her öğe içinde 'hekimSlotList' var) ya da tek bir dict olabilir.
        """
        results: List[Appointment] = []

        items = response_data if isinstance(response_data, list) else [response_data]

        for item in items:
            # Her item muhtemelen {"hekimSlotList": [...] , ...}
            doctor_schedule_slot = item.get("hekimSlotList", [])
            if doctor_schedule_slot:
                results.extend(cls.get_appointment_list_from_doctor_schedule_slot(doctor_schedule_slot))

        return results