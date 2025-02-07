import logging
import aiofiles
from datetime import timedelta
from aiohttp import ClientSession
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import (
    DOMAIN,
    URL_LOGIN,
    HEADERS_LOGIN,
    HEADERS_POST,
    URL_HOME,
    URL_INDEX,
    URL_RECEIPTS,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)

class EBlocDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordonator pentru actualizarea datelor în integrarea E-bloc."""

    def __init__(self, hass, config):
        """Inițializare coordonator."""
        super().__init__(
            hass,
            _LOGGER,
            name="EBlocDataUpdateCoordinator",
            update_interval=SCAN_INTERVAL,
        )
        self.hass = hass
        self.config = config
        self.session = None
        self.authenticated = False

    async def _async_update_data(self):
        """Actualizează datele pentru toate componentele."""
        try:
            if not self.session:
                self.session = ClientSession()
            if not self.authenticated:
                await self._authenticate()

            return {
                "home": await self._fetch_data(URL_HOME, {"pIdAsoc": self.config["pIdAsoc"], "pIdAp": self.config["pIdAp"]}),
                "index": await self._fetch_data(URL_INDEX, {"pIdAsoc": self.config["pIdAsoc"], "pLuna": "2024-12", "pIdAp": self.config["pIdAp"]}),
                "receipts": await self._fetch_data(URL_RECEIPTS, {"pIdAsoc": self.config["pIdAsoc"], "pIdAp": self.config["pIdAp"]}),
            }
        except Exception as e:
            raise UpdateFailed(f"Eroare la actualizarea datelor: {e}")

    async def _authenticate(self):
        """Autentificare pe server."""
        payload = {"pUser": self.config["pUser"], "pPass": self.config["pPass"]}
        try:
            async with self.session.post(URL_LOGIN, data=payload, headers=HEADERS_LOGIN) as response:
                if response.status == 200 and "Acces online proprietari" in await response.text():
                    _LOGGER.debug("Autentificare reușită.")
                    self.authenticated = True
                else:
                    raise UpdateFailed("Autentificare eșuată.")
        except Exception as e:
            raise UpdateFailed(f"Eroare la autentificare: {e}")

    async def _fetch_data(self, url, payload):
        """Execută cererea POST și returnează răspunsul JSON."""
        try:
            async with self.session.post(url, data=payload, headers=HEADERS_POST) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.error("Eroare la accesarea %s: Status %s", url, response.status)
                    return {}
        except Exception as e:
            _LOGGER.error("Eroare la conexiunea cu serverul: %s", e)
            return {}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Setăm senzorii pentru integrarea E-bloc."""
    coordinator = EBlocDataUpdateCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        EBlocHomeSensor(coordinator),
        EBlocContoareSensor(coordinator),
        EBlocPlatiChitanteSensor(coordinator),
    ]
    async_add_entities(sensors, update_before_add=True)


class EBlocSensorBase(SensorEntity):
    """Clasă de bază pentru senzorii E-bloc."""

    def __init__(self, coordinator, name):
        self._coordinator = coordinator
        self._attr_name = name
        self._attr_state = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):
        """Actualizează datele pentru senzor."""
        await self._coordinator.async_request_refresh()


class EBlocHomeSensor(EBlocSensorBase):
    """Senzor pentru `AjaxGetHomeApInfo.php`."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "Date client")

    async def async_update(self):
        """Actualizează datele pentru senzorul `home`."""
        data = self._coordinator.data.get("home", {}).get("1", {})
        self._attr_state = data.get("cod_client", "Necunoscut")
        self._attr_extra_state_attributes = {
            "cod_client": data.get("cod_client", "Necunoscut"),
            "apartament": data.get("ap", "Necunoscut"),
            "persoane_declarate": data.get("nr_pers_afisat", "Necunoscut"),
            "restanta_de_plata": f"{int(data.get('datorie', 0)) / 100:.2f} RON"
            if data.get("datorie") != "Necunoscut"
            else "Necunoscut",
            "ultima_zi_de_plata": data.get("ultima_zi_plata", "Necunoscut"),
            "contor_trimis": "Da"
            if data.get("contoare_citite", "Necunoscut") == "1"
            else "Nu",
            "incepere_citire_contoare": data.get("citire_contoare_start", "Necunoscut"),
            "incheiere_citire_contoare": data.get("citire_contoare_end", "Necunoscut"),
            "luna_cu_datoria_cea_mai_veche": data.get("luna_veche", "Necunoscut"),
            "luna_afisata": data.get("luna_afisata", "Necunoscut"),
            "nivel_restanta": data.get("nivel_restanta", "Necunoscut"),
        }

    @property
    def unique_id(self):
        return f"{DOMAIN}_client"

    @property
    def name(self):
        return self._attr_name

    @property
    def state(self):
        return self._attr_state

    @property
    def extra_state_attributes(self):
        return self._attr_extra_state_attributes

    @property
    def icon(self):
        """Pictograma senzorului."""
        return "mdi:account-file"

    @property
    def device_info(self):
        """Returnează informațiile dispozitivului."""
        return {
            "identifiers": {(DOMAIN, "home")},
            "name": "Interfață UI pentru E-bloc.ro",
            "manufacturer": "E-bloc.ro",
            "model": "Interfață UI pentru E-bloc.ro",
            "entry_type": DeviceEntryType.SERVICE,
        }

class EBlocContoareSensor(EBlocSensorBase):
    """Senzor pentru `AjaxGetIndexContoare.php`."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "Index contor")

    async def async_update(self):
        """Actualizează datele pentru senzorul `index`."""
        data = self._coordinator.data.get("index", {}).get("2", {})
        index_vechi = data.get("index_vechi", "").strip()
        index_nou = data.get("index_nou", "").strip()

        # Eliminăm zecimalele (ultimele trei cifre)
        try:
            index_vechi = (
                f"{int(float(index_vechi) // 1000)}" if index_vechi else "Necunoscut"
            )
        except ValueError:
            index_vechi = "Necunoscut"

        try:
            index_nou = (
                f"{int(float(index_nou) // 1000)}" if index_nou else "Necunoscut"
            )
        except ValueError:
            index_nou = "Necunoscut"

        # Setăm starea senzorului pentru `index_vechi`
        self._attr_state = (
            f"{index_vechi} mc" if index_vechi != "Necunoscut" else "Necunoscut"
        )

        # Atribute suplimentare
        self._attr_extra_state_attributes = {
            "index_vechi": f"{index_vechi} mc"
            if index_vechi != "Necunoscut"
            else "Necunoscut",
            "index_nou": f"{index_nou} mc"
            if index_nou != "Necunoscut"
            else "",
        }

    @property
    def unique_id(self):
        return f"{DOMAIN}_contor"

    @property
    def name(self):
        return self._attr_name

    @property
    def state(self):
        return self._attr_state

    @property
    def extra_state_attributes(self):
        return self._attr_extra_state_attributes

    @property
    def icon(self):
        """Pictograma senzorului."""
        return "mdi:counter"

    @property
    def device_info(self):
        """Returnează informațiile dispozitivului."""
        return {
            "identifiers": {(DOMAIN, "home")},
            "name": "Interfață UI pentru E-bloc.ro",
            "manufacturer": "E-bloc.ro",
            "model": "Interfață UI pentru E-bloc.ro",
            "entry_type": DeviceEntryType.SERVICE,
        }

class EBlocPlatiChitanteSensor(EBlocSensorBase):
    """Senzor pentru `AjaxGetPlatiChitanteToti.php`."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "Plăți și chitanțe")

    async def async_update(self):
        """Actualizează datele pentru senzorul `plati_chitante`."""
        data = self._coordinator.data.get("receipts", {})
        numar_chitante = len(data)

        # Setăm starea senzorului pe baza numărului de chitanțe
        self._attr_state = numar_chitante

        # Creăm atribute suplimentare
        atribute = {"Număr total de chitanțe": numar_chitante}
        for idx, chitanta_data in data.items():
            numar = chitanta_data.get("numar", "Necunoscut")
            data_chitanta = chitanta_data.get("data", "Necunoscut")
            suma = chitanta_data.get("suma", "0")
            suma_formatata = f"{int(suma) / 100:.2f} RON"

            # Formatul exact al atributelor (fără "Chitanță X")
            atribute[f"chitanta {idx}"] = numar
            atribute[f"data_{idx}"] = data_chitanta
            atribute[f"suma_platita_{idx}"] = suma_formatata

        # Atribuim atributele suplimentare
        self._attr_extra_state_attributes = atribute

    @property
    def unique_id(self):
        return f"{DOMAIN}_plati_si_chitante"

    @property
    def name(self):
        return self._attr_name

    @property
    def state(self):
        return self._attr_state

    @property
    def extra_state_attributes(self):
        return self._attr_extra_state_attributes

    @property
    def icon(self):
        """Pictograma senzorului."""
        return "mdi:credit-card-check-outline"

    @property
    def device_info(self):
        """Returnează informațiile dispozitivului."""
        return {
            "identifiers": {(DOMAIN, "home")},
            "name": "Interfață UI pentru E-bloc.ro",
            "manufacturer": "E-bloc.ro",
            "model": "Interfață UI pentru E-bloc.ro",
            "entry_type": DeviceEntryType.SERVICE,
        }
