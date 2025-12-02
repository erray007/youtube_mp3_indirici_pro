# globalPlugins/__init__.py

import globalPluginHandler
import wx
import threading
import os
import sys
import json
import subprocess
import webbrowser
import locale
import urllib.request
import addonHandler
import gui
import ui
import time
import struct
import ctypes
from logHandler import log

# --- YOL VE SABİT AYARLARI ---
addon_dir = os.path.dirname(__file__)
lib_path = os.path.join(addon_dir, "lib")
lang_path = os.path.join(addon_dir, "languages")
ffmpeg_klasoru = os.path.join(lib_path, "ffmpeg")
ffmpeg_exe = os.path.join(ffmpeg_klasoru, "ffmpeg.exe")
ffprobe_exe = os.path.join(ffmpeg_klasoru, "ffprobe.exe")
config_dosyasi = os.path.join(addon_dir, "config.json")
playlist_dosyasi = os.path.join(addon_dir, "playlists.json")

# GitHub Depo Bilgileri
GITHUB_USER = "erray007"
GITHUB_REPO = "youtube_mp3_indirici_pro"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

# yt-dlp Yükleme
yt_dlp = None
kutuphane_hatasi = None
try:
    import yt_dlp
except Exception as e:
    kutuphane_hatasi = str(e)
    log.error(f"Kütüphane Hatası: {kutuphane_hatasi}")

# --- AYARLAR ---
varsayilan_ayarlar = {
    "indirme_klasoru": os.path.join(os.path.expanduser("~"), "Downloads"),
    "arama_sonuc_sayisi": 15,
    "video_kalitesi_idx": 0, 
    "ses_kalitesi_idx": 1,
    "dil": "auto",
    "otomatik_guncelleme": True,
    "ses_cihazi": -1 # -1 Varsayılan cihaz
}

def ayarlari_yukle():
    ayarlar = varsayilan_ayarlar.copy()
    if os.path.exists(config_dosyasi):
        try:
            with open(config_dosyasi, "r", encoding="utf-8") as f:
                ayarlar.update(json.load(f))
        except: pass
    
    # GÜVENLİK KONTROLÜ: Klasör yerinde mi?
    klasor = ayarlar.get("indirme_klasoru", "")
    if not klasor or not os.path.exists(klasor):
        ayarlar["indirme_klasoru"] = varsayilan_ayarlar["indirme_klasoru"]
        
    return ayarlar

def ayarlari_kaydet(ayarlar):
    try:
        with open(config_dosyasi, "w", encoding="utf-8") as f:
            json.dump(ayarlar, f, indent=4)
    except: pass

# --- DİL YÖNETİCİSİ ---
class DilYoneticisi:
    def __init__(self):
        self.sozluk = {}
        self.varsayilan_yukle()
        conf = ayarlari_yukle()
        self.dil_yukle(conf.get("dil", "auto"))
        
    def varsayilan_yukle(self):
        self.sozluk = {
            "menu_name": "YouTube Pro İndirici",
            "menu_desc": "YouTube video ve ses indirici",
            "title_main": "YouTube Pro İndirici",
            "title_player": "Oynatıcı",
            "title_confirm": "Onay",
            "btn_close": "Kapat",
            "err_title": "Hata",
            "msg_saved": "Ayarlar kaydedildi.",
            "upd_checking": "Güncellemeler kontrol ediliyor...",
            "upd_new_found": "Yeni sürüm bulundu: {v}\nİndirip kurmak ister misiniz?",
            "upd_latest": "Sürümünüz güncel. Zaten en son sürümü kullanıyorsunuz.",
            "upd_error": "Güncelleme kontrolü başarısız oldu.",
            "upd_downloading": "Güncelleme indiriliyor...",
            "upd_ready": "Güncelleme indi. Kurulum başlatılıyor...",
            "lbl_release_notes": "Sürüm Notları:",
            "btn_update": "Güncelle",
            "btn_cancel": "İptal",
            "btn_check_now": "Güncellemeleri Şimdi Kontrol Et",
            "chk_auto_update": "Açılışta güncellemeleri otomatik kontrol et",
            "tab_search": "Ara ve İndir",
            "tab_playlist": "Oynatma Listeleri",
            "tab_settings": "Ayarlar",
            "lbl_search": "Arama veya Link:",
            "btn_find": "Bul / Getir",
            "lbl_results": "Sonuçlar:",
            "msg_searching": "İşleniyor...",
            "msg_no_result": "Sonuç bulunamadı.",
            "msg_items_listed": "öğe listelendi.",
            "msg_downloading": "İndiriliyor",
            "msg_cancelled": "İptal Edildi",
            "msg_download_started": "İndirme Başlıyor",
            "msg_completed": "Tamamlandı",
            "msg_added": "Eklendi.",
            "msg_exists": "Zaten listede var.",
            "msg_confirm_delete": "Silinsin mi?",
            "ctx_play_bass": "YouTube Pro ile Oynat (BASS)",
            "ctx_play": "Varsayılan Oynatıcıda Aç",
            "ctx_browser": "Tarayıcıda Aç",
            "ctx_download_video": "Video Olarak İndir",
            "ctx_download_audio": "Ses Olarak İndir",
            "ctx_add_playlist": "Playlist'e Ekle",
            "ctx_new_playlist": "Yeni Liste Oluştur...",
            "lbl_lists": "Listelerim:",
            "lbl_content": "İçerik:",
            "btn_new": "Yeni Liste",
            "btn_play": "Oynat",
            "ctx_rename": "Yeniden Adlandır",
            "ctx_delete": "Sil",
            "ctx_export": "M3U Olarak Kaydet",
            "lbl_folder": "İndirme Klasörü:",
            "lbl_video_quality": "Video Çözünürlüğü:",
            "lbl_audio_quality": "Ses Kalitesi:",
            "lbl_limit": "Arama Sonuç Limiti:",
            "lbl_device": "Ses Çıkış Cihazı:",
            "btn_save": "Ayarları Kaydet",
            "val_best": "En İyi (Otomatik)",
            "val_high": "Yüksek",
            "val_std": "Standart",
            "val_low": "Düşük",
            "input_list_name": "Liste Adı:",
            "err_lib": "Kütüphane Hatası",
            "err_ffmpeg": "FFmpeg eksik",
            "status_playing": "Oynatılıyor",
            "status_paused": "Duraklatıldı",
            "msg_buffering": "Bağlantı kuruluyor...",
            "btn_play_pause": "Oynat / Duraklat",
            "btn_rewind": "Başa Sar"
        }

    def dil_yukle(self, secim="auto"):
        try:
            self.varsayilan_yukle()
            hedef_kod = "tr"
            if secim == "auto":
                hedef_kod = languageHandler.getLanguage().split('_')[0]
            else:
                hedef_kod = secim
            target_file = os.path.join(lang_path, f"{hedef_kod}.json")
            if not os.path.exists(target_file):
                target_file = os.path.join(lang_path, "tr.json")
            if os.path.exists(target_file):
                with open(target_file, "r", encoding="utf-8") as f:
                    veri = json.load(f)
                    self.sozluk.update(veri)
        except Exception as e:
            log.error(f"Dil yükleme hatası: {e}")

    def get(self, key, **kwargs):
        val = self.sozluk.get(key, key)
        if kwargs:
            try: return val.format(**kwargs)
            except: return val
        return val

dil = DilYoneticisi()

# --- GÜNCELLEME YÖNETİCİSİ ---
class GuncellemeYoneticisi:
    def __init__(self):
        self.mevcut_surum = "0.0"
        try:
            self.mevcut_surum = addonHandler.getCodeAddon().manifest['version']
        except: pass

    def surum_karsilastir(self, v1, v2):
        def parse(v):
            parts = []
            for x in v.replace('v','').split('.'):
                if x.isdigit(): parts.append(int(x))
            return parts
        p1 = parse(v1)
        p2 = parse(v2)
        return p1 < p2

    def kontrol_et(self, sessiz=False):
        threading.Thread(target=self._kontrol_thread, args=(sessiz,)).start()

    def _kontrol_thread(self, sessiz):
        if not sessiz: wx.CallAfter(ui.message, dil.get("upd_checking"))
        try:
            req = urllib.request.Request(GITHUB_API_URL)
            req.add_header('User-Agent', 'NVDA-Addon')
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            remote_ver = data.get("tag_name", "0.0")
            aciklama = data.get("body", "Sürüm notu bulunamadı.")
            download_url = None
            
            for asset in data.get("assets", []):
                if asset["name"].endswith(".nvda-addon"):
                    download_url = asset["browser_download_url"]
                    break
            
            if self.surum_karsilastir(self.mevcut_surum, remote_ver):
                if download_url:
                    wx.CallAfter(self.guncelleme_diyalogu_ac, remote_ver, aciklama, download_url)
            else:
                if not sessiz: wx.CallAfter(ui.message, dil.get("upd_latest"))
                
        except Exception as e:
            log.error(f"Update Error: {e}")
            if not sessiz: wx.CallAfter(ui.message, dil.get("upd_error"))

    def guncelleme_diyalogu_ac(self, yeni_surum, notlar, url):
        dlg = wx.Dialog(None, title=dil.get("title_main"), size=(500, 400), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        pnl = wx.Panel(dlg)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        lbl_info = wx.StaticText(pnl, label=dil.get("upd_new_found", v=yeni_surum))
        sizer.Add(lbl_info, 0, wx.ALL, 10)
        sizer.Add(wx.StaticText(pnl, label=dil.get("lbl_release_notes")), 0, wx.LEFT, 10)
        txt_notlar = wx.TextCtrl(pnl, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        txt_notlar.SetValue(notlar)
        sizer.Add(txt_notlar, 1, wx.EXPAND | wx.ALL, 10)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_update = wx.Button(pnl, wx.ID_YES, label=dil.get("btn_update"))
        btn_cancel = wx.Button(pnl, wx.ID_NO, label=dil.get("btn_cancel"))
        btn_sizer.Add(btn_update, 0, wx.RIGHT, 10)
        btn_sizer.Add(btn_cancel, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        pnl.SetSizer(sizer)
        btn_update.Bind(wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_YES))
        btn_cancel.Bind(wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_NO))
        
        dlg.Centre()
        dlg.Raise()
        txt_notlar.SetFocus()
        
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            self.progress_dialog_ile_indir(url)
        else:
            dlg.Destroy()

    def progress_dialog_ile_indir(self, url):
        self.pd = wx.ProgressDialog(
            dil.get("title_main"),
            dil.get("upd_downloading"),
            maximum=100,
            parent=None,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT
        )
        self.pd.Centre()
        self.pd.Raise()
        threading.Thread(target=self.indir_worker, args=(url,)).start()

    def indir_worker(self, url):
        try:
            temp_path = os.path.join(os.getenv("TEMP"), "update.nvda-addon")
            with urllib.request.urlopen(url) as response:
                total_size = int(response.info().get('Content-Length', 0))
                block_size = 8192
                count = 0
                with open(temp_path, "wb") as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer: break
                        f.write(buffer)
                        count += len(buffer)
                        if total_size > 0:
                            percent = int(count * 100 / total_size)
                            wx.CallAfter(self.pd.Update, percent, f"%{percent}")
            
            wx.CallAfter(self.pd.Destroy)
            wx.CallAfter(ui.message, dil.get("upd_ready"))
            os.startfile(temp_path)
        except Exception as e:
            wx.CallAfter(self.pd.Destroy)
            wx.CallAfter(ui.message, dil.get("upd_error") + f" {e}")

update_manager = GuncellemeYoneticisi()

# --- BASS PLAYER MOTORU (GELİŞMİŞ) ---
class BASS_DEVICEINFO(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("driver", ctypes.c_char_p),
        ("flags", ctypes.c_ulong)
    ]

class GelismisPlayer:
    def __init__(self):
        self.bass = None
        self.stream_handle = 0
        self.playing = False
        self.paused = False
        self.volume = 1.0 
        self.duration = 0
        self.bass_path = None
        self.device_id = -1 
        
        self.BASS_STREAM_AUTOFREE = 0x40000
        self.BASS_POS_BYTE = 0
        self.BASS_ATTRIB_VOL = 2
        self.BASS_CONFIG_NET_BUFFER = 21 
        self.BASS_DEVICE_ENABLED = 1
        
        self._dll_bul_ve_yukle()
        
        # Kayıtlı cihazı yükle
        conf = ayarlari_yukle()
        self.init_device(conf.get("ses_cihazi", -1))

    def _dll_bul_ve_yukle(self):
        is_64_bit = (struct.calcsize("P") * 8) == 64
        
        if is_64_bit:
            hedef_dosyalar = ["bass64.dll", "bass.dll"]
        else:
            hedef_dosyalar = ["bass32.dll", "bass.dll"]

        self.bass_path = None
        klasorler = [lib_path, addon_dir]
        
        for dosya_adi in hedef_dosyalar:
            for klasor in klasorler:
                tam_yol = os.path.join(klasor, dosya_adi)
                if os.path.exists(tam_yol):
                    self.bass_path = tam_yol
                    break
            if self.bass_path: break
        
        if not self.bass_path:
            log.error("YouTubePro: BASS DLL bulunamadı.")
            return

        try:
            self.bass = ctypes.CDLL(self.bass_path)
            self.bass.BASS_Init.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
            self.bass.BASS_Free.argtypes = []
            self.bass.BASS_GetDeviceInfo.argtypes = [ctypes.c_int, ctypes.POINTER(BASS_DEVICEINFO)]
            self.bass.BASS_GetDeviceInfo.restype = ctypes.c_int
            self.bass.BASS_StreamCreateURL.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
            self.bass.BASS_StreamCreateURL.restype = ctypes.c_ulong
            self.bass.BASS_ChannelPlay.argtypes = [ctypes.c_ulong, ctypes.c_int]
            self.bass.BASS_ChannelStop.argtypes = [ctypes.c_ulong]
            self.bass.BASS_ChannelPause.argtypes = [ctypes.c_ulong]
            self.bass.BASS_ChannelSetAttribute.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_float]
            self.bass.BASS_ChannelSetPosition.argtypes = [ctypes.c_ulong, ctypes.c_longlong, ctypes.c_int]
            self.bass.BASS_ChannelBytes2Seconds.argtypes = [ctypes.c_ulong, ctypes.c_longlong]
            self.bass.BASS_ChannelBytes2Seconds.restype = ctypes.c_double
            self.bass.BASS_ChannelGetPosition.argtypes = [ctypes.c_ulong, ctypes.c_int]
            self.bass.BASS_ChannelGetPosition.restype = ctypes.c_longlong
            self.bass.BASS_StreamFree.argtypes = [ctypes.c_ulong]
            self.bass.BASS_SetConfig.argtypes = [ctypes.c_int, ctypes.c_int]
        except Exception as e:
            log.error(f"BASS Yükleme Hatası: {e}")

    def get_audio_devices(self):
        devices = []
        if not self.bass: return []
        
        info = BASS_DEVICEINFO()
        i = 1 
        while self.bass.BASS_GetDeviceInfo(i, ctypes.byref(info)):
            if info.flags & self.BASS_DEVICE_ENABLED:
                try: name = info.name.decode('mbcs')
                except: name = str(info.name)
                devices.append((i, name))
            i += 1
        
        devices.insert(0, (-1, "Varsayılan Ses Cihazı"))
        return devices

    def init_device(self, device_id):
        if not self.bass: return
        self.device_id = device_id
        
        self.durdur(tamamen=False)
        self.bass.BASS_Free()
        
        if not self.bass.BASS_Init(device_id, 44100, 0, 0, 0):
            self.bass.BASS_Init(-1, 44100, 0, 0, 0)
            
        self.bass.BASS_SetConfig(self.BASS_CONFIG_NET_BUFFER, 15000)

    def baslat(self, url, duration=0, start_time=0):
        if not self.bass: return

        self.durdur(tamamen=False)
        self.duration = duration
        
        try:
            url_bytes = url.encode('utf-8')
        except:
            url_bytes = url.encode('mbcs') 
        
        self.stream_handle = self.bass.BASS_StreamCreateURL(url_bytes, 0, self.BASS_STREAM_AUTOFREE, None, 0)
        
        if self.stream_handle == 0:
            err = self.bass.BASS_ErrorGetCode()
            if err == 8: # Init hatası
                 self.init_device(self.device_id)
                 self.stream_handle = self.bass.BASS_StreamCreateURL(url_bytes, 0, self.BASS_STREAM_AUTOFREE, None, 0)

            if self.stream_handle == 0:
                wx.CallAfter(ui.message, "Oynatma hatası!")
                return

        self.playing = True
        self.paused = False
        
        if start_time > 0:
            self.seek_to(start_time)
        
        self.set_volume(self.volume)
        self.bass.BASS_ChannelPlay(self.stream_handle, False)
        
    def durdur(self, tamamen=True):
        if self.bass and self.stream_handle:
            self.bass.BASS_ChannelStop(self.stream_handle)
            self.bass.BASS_StreamFree(self.stream_handle)
            self.stream_handle = 0
        
        self.playing = False
        self.paused = False

    def toggle_pause(self):
        if not self.bass or not self.stream_handle: return False
        
        if self.paused:
            self.bass.BASS_ChannelPlay(self.stream_handle, False)
            self.paused = False
        else:
            self.bass.BASS_ChannelPause(self.stream_handle)
            self.paused = True
        return self.paused

    def sar(self, saniye):
        if not self.bass or not self.stream_handle: return
        current = self.get_time()
        self.seek_to(current + saniye)

    def seek_to(self, saniye):
        if not self.bass or not self.stream_handle: return
        if saniye < 0: saniye = 0
        if self.duration > 0 and saniye > self.duration: saniye = self.duration
        
        pos_bytes = self.bass.BASS_ChannelSeconds2Bytes(self.stream_handle, ctypes.c_double(saniye))
        self.bass.BASS_ChannelSetPosition(self.stream_handle, pos_bytes, self.BASS_POS_BYTE)

    def get_time(self):
        if not self.bass or not self.stream_handle: return 0
        pos = self.bass.BASS_ChannelGetPosition(self.stream_handle, self.BASS_POS_BYTE)
        if pos == -1: return 0
        sec = self.bass.BASS_ChannelBytes2Seconds(self.stream_handle, pos)
        return sec

    def set_volume(self, val):
        self.volume = max(0.0, min(1.0, val))
        if self.bass and self.stream_handle:
            self.bass.BASS_ChannelSetAttribute(self.stream_handle, self.BASS_ATTRIB_VOL, ctypes.c_float(self.volume))

# --- PLAYER PENCERESİ (Bağımsız, Sessiz Slider) ---
class PlayerPenceresi(wx.Frame):
    def __init__(self, player_instance, baslik, sure_str):
        super().__init__(parent=None, title=f"{dil.get('title_player')} - {baslik}", size=(600, 220), style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
        
        self.player = player_instance
        self.duration_sec = self.parse_duration(sure_str)
        self.baslik = baslik
        self.sure_str = sure_str
        self.kapanma_sinyali = False
        self.ui_guncelleniyor = False
        
        self.Center()
        self.panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.lbl_info = wx.StaticText(self.panel, label=f"Oynatılıyor: {baslik}")
        sizer.Add(self.lbl_info, 0, wx.ALL, 10)
        
        self.slider = wx.Slider(self.panel, value=0, minValue=0, maxValue=int(self.duration_sec) if self.duration_sec > 0 else 100, style=wx.SL_HORIZONTAL)
        self.slider.Bind(wx.EVT_SLIDER, self.on_slider_change)
        sizer.Add(self.slider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        
        self.lbl_time = wx.StaticText(self.panel, label=f"00:00 / {sure_str}")
        sizer.Add(self.lbl_time, 0, wx.ALIGN_CENTER | wx.TOP, 5)
        
        # BUTONLAR
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_basa = wx.Button(self.panel, label=dil.get("btn_rewind"))
        self.btn_basa.Bind(wx.EVT_BUTTON, self.on_basa_sar)
        btn_sizer.Add(self.btn_basa, 0, wx.ALL, 5)

        self.btn_oynat = wx.Button(self.panel, label=dil.get("btn_play_pause"))
        self.btn_oynat.Bind(wx.EVT_BUTTON, self.on_oynat_duraklat)
        btn_sizer.Add(self.btn_oynat, 0, wx.ALL, 5)
        
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        
        self.lbl_status = wx.StaticText(self.panel, label=dil.get("msg_buffering"))
        sizer.Add(self.lbl_status, 0, wx.ALIGN_CENTER | wx.BOTTOM, 5)

        self.panel.SetSizer(sizer)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_ui, self.timer)
        self.timer.Start(500) 
        
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.Show()
        self.Raise()
        self.SetFocus()
        self.btn_oynat.SetFocus() # Butona odaklan
        ui.message(f"Oynatıcı açıldı. {baslik}")

    def parse_duration(self, s):
        try:
            parts = list(map(int, s.split(':')))
            if len(parts) == 2: return parts[0]*60 + parts[1]
            if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
            return 0
        except: return 0

    def sec_to_str(self, sec):
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def update_ui(self, event):
        if self.kapanma_sinyali or not self: return
        try:
            if not self.player.playing: return
            cur = self.player.get_time()
            
            self.ui_guncelleniyor = True
            if not wx.GetMouseState().LeftIsDown():
                self.slider.SetValue(int(cur))
            self.ui_guncelleniyor = False
            
            cur_str = self.sec_to_str(cur)
            self.lbl_time.SetLabel(f"{cur_str} / {self.sure_str}")
            status = dil.get("status_paused") if self.player.paused else dil.get("status_playing")
            self.lbl_status.SetLabel(status)
        except: self.timer.Stop()

    def on_slider_change(self, event):
        if self.ui_guncelleniyor: return
        val = self.slider.GetValue()
        self.player.seek_to(val)
        ui.message(f"Konum: {self.sec_to_str(val)}")

    def on_oynat_duraklat(self, event):
        durum = self.player.toggle_pause()
        msg = dil.get("status_paused") if durum else dil.get("status_playing")
        ui.message(msg)
        self.btn_oynat.SetFocus()

    def on_basa_sar(self, event):
        self.player.seek_to(0)
        ui.message("Başa sarıldı")
        self.btn_oynat.SetFocus()

    def on_key(self, event):
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE: self.Close()
        elif code == wx.WXK_SPACE: self.on_oynat_duraklat(None)
        elif code == wx.WXK_RIGHT:
            self.player.sar(10)
            ui.message(self.sec_to_str(self.player.get_time()))
        elif code == wx.WXK_LEFT:
            self.player.sar(-10)
            ui.message(self.sec_to_str(self.player.get_time()))
        elif code == wx.WXK_UP:
            self.player.set_volume(self.player.volume + 0.05)
            ui.message(f"Ses: %{int(self.player.volume * 100)}")
        elif code == wx.WXK_DOWN:
            self.player.set_volume(self.player.volume - 0.05)
            ui.message(f"Ses: %{int(self.player.volume * 100)}")
        elif code == ord('T') or code == ord('t'):
            cur = self.player.get_time()
            ui.message(f"{self.sec_to_str(cur)} / {self.sure_str}")
        else: event.Skip()

    def on_close(self, event):
        self.kapanma_sinyali = True
        if self.timer.IsRunning(): self.timer.Stop()
        self.player.durdur(tamamen=True)
        self.Destroy()

# --- DURUM TAKİBİ ---
aktif_indirmeler = {}
indirme_kilidi = threading.Lock()
VIDEO_KALITE_MAP = [None, 1080, 720, 480] 
SES_KALITE_MAP = ["320", "192", "128"]

def playlistleri_yukle():
    if os.path.exists(playlist_dosyasi):
        try:
            with open(playlist_dosyasi, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def playlistleri_kaydet(data):
    try:
        with open(playlist_dosyasi, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

# --- YARDIMCI FONKSİYONLAR ---
def sistemde_ac(url):
    try:
        if sys.platform == 'win32':
            os.startfile(url)
        else:
            subprocess.Popen(['xdg-open', url])
    except Exception as e: wx.MessageBox(str(e), dil.get("err_title"))

def tarayicida_ac(url):
    webbrowser.open(url)

# --- GLOBAL PLUGIN ---
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super().__init__()
        self.menu_item = gui.mainFrame.sysTrayIcon.toolsMenu.Append(wx.ID_ANY, dil.get("menu_name"), dil.get("menu_desc"))
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.on_menu_click, self.menu_item)
        
        conf = ayarlari_yukle()
        if conf.get("otomatik_guncelleme", True):
            update_manager.kontrol_et(sessiz=True)

    def on_menu_click(self, event):
        self.script_arayuzuAc(None)

    def script_arayuzuAc(self, gesture):
        conf = ayarlari_yukle()
        dil.dil_yukle(conf.get("dil", "auto"))
        if yt_dlp is None:
            wx.MessageBox(f"{dil.get('err_lib')}:\n{kutuphane_hatasi}", dil.get("err_title"))
            return
        if not os.path.exists(ffmpeg_exe):
            wx.MessageBox(f"{dil.get('err_ffmpeg')}{ffmpeg_klasoru}", dil.get("err_title"))
            
        if hasattr(self, 'pencere') and self.pencere:
            try:
                self.pencere.Raise()
                self.pencere.SetFocus()
                return
            except: pass 
            
        self.pencere = AnaPencere(self)

    def arayuzu_yenile(self):
        if hasattr(self, 'pencere') and self.pencere:
            self.pencere.Destroy()
        conf = ayarlari_yukle()
        dil.dil_yukle(conf.get("dil", "auto"))
        self.pencere = AnaPencere(self)
        self.pencere.Show()

    def terminate(self):
        try: 
            gui.mainFrame.sysTrayIcon.toolsMenu.RemoveItem(self.menu_item)
        except: pass
        super().terminate()

# --- ARAYÜZ ---
class AnaPencere(wx.Frame):
    def __init__(self, plugin_instance):
        super().__init__(parent=gui.mainFrame, title=dil.get("title_main"), size=(700, 600))
        self.plugin_instance = plugin_instance 
        
        self.mevcut_ayarlar = ayarlari_yukle()
        self.playlistler = playlistleri_yukle()
        
        # Player Motorunu Başlat
        self.player_engine = GelismisPlayer()
        
        self.panel = wx.Panel(self)
        ana_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)
        
        self.sekme_ara = AraVeIndirSekmesi(self.notebook, self)
        self.sekme_playlist = OynatmaListesiSekmesi(self.notebook, self)
        self.sekme_ayarlar = AyarlarSekmesi(self.notebook, self)
        
        self.notebook.AddPage(self.sekme_ara, dil.get("tab_search"))
        self.notebook.AddPage(self.sekme_playlist, dil.get("tab_playlist"))
        self.notebook.AddPage(self.sekme_ayarlar, dil.get("tab_settings"))
        
        ana_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        btn_kapat = wx.Button(self.panel, label=dil.get("btn_close"))
        btn_kapat.Bind(wx.EVT_BUTTON, self.kapat)
        ana_sizer.Add(btn_kapat, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.Bind(wx.EVT_CLOSE, self.kapat)
        self.Bind(wx.EVT_CHAR_HOOK, self.tus_yakala)
        self.panel.SetSizer(ana_sizer)
        self.Center()
        self.Show()

    def tus_yakala(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE: self.Close()
        else: event.Skip()
    def kapat(self, event): self.Destroy()

# --- 1. ARA VE İNDİR ---
class AraVeIndirSekmesi(wx.Panel):
    def __init__(self, parent, ana_pencere):
        super().__init__(parent)
        self.ana_pencere = ana_pencere
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=dil.get("lbl_search")), 0, wx.TOP|wx.LEFT, 10)
        self.txt_ara = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.txt_ara.Bind(wx.EVT_TEXT_ENTER, self.aramayi_baslat)
        sizer.Add(self.txt_ara, 0, wx.EXPAND|wx.ALL, 10)
        self.btn_ara = wx.Button(self, label=dil.get("btn_find"))
        self.btn_ara.Bind(wx.EVT_BUTTON, self.aramayi_baslat)
        sizer.Add(self.btn_ara, 0, wx.ALL, 5)
        sizer.Add(wx.StaticText(self, label=dil.get("lbl_results")), 0, wx.LEFT|wx.TOP, 10)
        self.liste = wx.ListBox(self, style=wx.LB_SINGLE)
        self.liste.Bind(wx.EVT_CONTEXT_MENU, self.baglam_menusu_ac)
        self.liste.Bind(wx.EVT_KEY_DOWN, self.klavye_kisayollari)
        sizer.Add(self.liste, 1, wx.EXPAND|wx.ALL, 10)
        self.video_verileri = [] 
        self.SetSizer(sizer)

    def aramayi_baslat(self, event):
        sorgu = self.txt_ara.GetValue().strip()
        if not sorgu: return
        ui.message(dil.get("msg_searching"))
        self.btn_ara.Disable()
        self.liste.Clear()
        if sorgu.startswith("http"):
            threading.Thread(target=self.arka_plan_url, args=(sorgu,)).start()
        else:
            limit = self.ana_pencere.mevcut_ayarlar["arama_sonuc_sayisi"]
            threading.Thread(target=self.arka_plan_ara, args=(sorgu, limit)).start()

    def arka_plan_ara(self, sorgu, limit):
        try:
            opts = {'quiet': True, 'extract_flat': True, 'noplaylist': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{sorgu}", download=False)
                entries = info.get('entries', []) if info else []
            wx.CallAfter(self.sonuclari_goster, entries)
        except Exception as e: wx.CallAfter(self.hata, str(e))

    def arka_plan_url(self, url):
        try:
            opts = {'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is None:
                    wx.CallAfter(self.hata, dil.get("msg_error"))
                    return
                entries = list(info['entries']) if 'entries' in info else [info]
            wx.CallAfter(self.sonuclari_goster, entries)
        except Exception as e: wx.CallAfter(self.hata, str(e))

    def sonuclari_goster(self, entries):
        self.btn_ara.Enable()
        self.video_verileri = []
        items = []
        if not entries:
            ui.message(dil.get("msg_no_result"))
            return
        for vid in entries:
            if vid:
                baslik = vid.get('title') or vid.get('id', 'Bilinmeyen')
                sure = vid.get('duration_string', '')
                kanal = vid.get('uploader', '')
                url = vid.get('url')
                v_id = vid.get('id')
                full_url = url if (url and "http" in str(url)) else (f"https://www.youtube.com/watch?v={v_id}" if v_id else url)
                self.video_verileri.append({'title': baslik, 'url': full_url, 'duration': sure})
                if sure: items.append(f"{baslik} - {kanal} [{sure}]")
                else: items.append(f"{baslik}" + (f" - {kanal}" if kanal else ""))
        self.liste.Set(items)
        if items:
            self.liste.SetSelection(0)
            self.liste.SetFocus()
            ui.message(f"{len(items)} {dil.get('msg_items_listed')}")

    def klavye_kisayollari(self, event):
        kod = event.GetKeyCode()
        if kod == wx.WXK_F5:
            ui.message(f"{len(aktif_indirmeler)} {dil.get('msg_downloading')}...")
            return
        sel = self.liste.GetSelection()
        if sel == wx.NOT_FOUND: event.Skip(); return
        url = self.video_verileri[sel]['url']
        baslik = self.video_verileri[sel]['title']
        if kod == wx.WXK_F1: indirme_baslatici(self.ana_pencere, url, baslik, 1)
        elif kod == wx.WXK_F2: indirme_baslatici(self.ana_pencere, url, baslik, 0)
        elif kod == wx.WXK_F3:
            durum = "Bekliyor"
            with indirme_kilidi:
                if url in aktif_indirmeler: durum = aktif_indirmeler[url]['status']
            ui.message(durum)
        elif kod == wx.WXK_F4:
            with indirme_kilidi:
                if url in aktif_indirmeler:
                    aktif_indirmeler[url]['cancel'] = True
                    ui.message(dil.get("msg_cancelled") + "...")
        else: event.Skip()

    def baglam_menusu_ac(self, event):
        sel = self.liste.GetSelection()
        if sel == wx.NOT_FOUND: return
        url = self.video_verileri[sel]['url']
        baslik = self.video_verileri[sel]['title']
        menu = wx.Menu()
        menu.Append(99, dil.get("ctx_play_bass")) # BASS Player
        menu.Append(1, dil.get("ctx_play"))
        menu.Append(2, dil.get("ctx_browser"))
        menu.AppendSeparator()
        dl_menu = wx.Menu()
        dl_menu.Append(3, dil.get("ctx_download_video"))
        dl_menu.Append(4, dil.get("ctx_download_audio"))
        menu.AppendSubMenu(dl_menu, dil.get("title_main")) 
        pl_menu = wx.Menu()
        pl_menu.Append(5, dil.get("ctx_new_playlist"))
        if self.ana_pencere.playlistler:
            pl_menu.AppendSeparator()
            for i, pl in enumerate(self.ana_pencere.playlistler.keys()):
                pl_menu.Append(100+i, pl)
        menu.AppendSubMenu(pl_menu, dil.get("ctx_add_playlist"))
        
        # BINDINGS
        self.Bind(wx.EVT_MENU, lambda e: self.bass_oynat(url, baslik), id=99)
        self.Bind(wx.EVT_MENU, lambda e: sistemde_ac(url), id=1)
        self.Bind(wx.EVT_MENU, lambda e: tarayicida_ac(url), id=2)
        self.Bind(wx.EVT_MENU, lambda e: indirme_baslatici(self.ana_pencere, url, baslik, 0), id=3)
        self.Bind(wx.EVT_MENU, lambda e: indirme_baslatici(self.ana_pencere, url, baslik, 1), id=4)
        self.Bind(wx.EVT_MENU, lambda e: self.yeni_pl(sel), id=5)
        for i, pl in enumerate(self.ana_pencere.playlistler.keys()):
            self.Bind(wx.EVT_MENU, lambda e, name=pl, idx=sel: self.ekle_pl(name, idx), id=100+i)
        self.PopupMenu(menu)
        menu.Destroy()

    def bass_oynat(self, url, baslik):
        ui.message(dil.get("msg_buffering"))
        threading.Thread(target=self._stream_hazirla, args=(url, baslik)).start()

    def _stream_hazirla(self, url, baslik):
        try:
            # m4a (AAC) formatını zorluyoruz
            opts = {
                'format': 'bestaudio[ext=m4a]/best', 
                'quiet': True,
                'noplaylist': True,
                'force_generic_extractor': False
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info['url']
                duration_sec = info.get('duration', 0)
                sure_str = info.get('duration_string', '0:00')
            
            wx.CallAfter(self._player_ac, stream_url, baslik, sure_str, duration_sec)
        except Exception as e:
            wx.CallAfter(wx.MessageBox, f"Hata: {e}", dil.get("err_title"))

    def _player_ac(self, url, baslik, sure_str, duration_sec):
        self.ana_pencere.player_engine.baslat(url, duration=duration_sec)
        PlayerPenceresi(self.ana_pencere.player_engine, baslik, sure_str)

    def yeni_pl(self, idx):
        dlg = wx.TextEntryDialog(self, dil.get("input_list_name"), dil.get("ctx_new_playlist"))
        if dlg.ShowModal() == wx.ID_OK:
            ad = dlg.GetValue().strip()
            if ad:
                if ad not in self.ana_pencere.playlistler: self.ana_pencere.playlistler[ad] = []
                self.ekle_pl(ad, idx)
        dlg.Destroy()

    def ekle_pl(self, ad, idx):
        vid = self.video_verileri[idx]
        if not any(v['url'] == vid['url'] for v in self.ana_pencere.playlistler[ad]):
            self.ana_pencere.playlistler[ad].append(vid)
            playlistleri_kaydet(self.ana_pencere.playlistler)
            if hasattr(self.ana_pencere.sekme_playlist, 'tazele'):
                self.ana_pencere.sekme_playlist.tazele()
            ui.message(dil.get("msg_added"))
        else: ui.message(dil.get("msg_exists"))

    def hata(self, msg):
        self.btn_ara.Enable()
        wx.MessageBox(msg, dil.get("err_title"))

# --- 2. PLAYLIST ---
class OynatmaListesiSekmesi(wx.Panel):
    def __init__(self, parent, ana_pencere):
        super().__init__(parent)
        self.ana_pencere = ana_pencere
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self, label=dil.get("lbl_lists")), 0, wx.ALL, 5)
        self.lb_sol = wx.ListBox(self)
        self.lb_sol.Bind(wx.EVT_LISTBOX, self.sec_sol)
        self.lb_sol.Bind(wx.EVT_CONTEXT_MENU, self.menu_sol)
        self.lb_sol.Bind(wx.EVT_KEY_DOWN, self.tus_sol)
        left.Add(self.lb_sol, 1, wx.EXPAND|wx.ALL, 5)
        btn_yeni = wx.Button(self, label=dil.get("btn_new"))
        btn_yeni.Bind(wx.EVT_BUTTON, self.yeni)
        left.Add(btn_yeni, 0, wx.EXPAND|wx.ALL, 5)
        right = wx.BoxSizer(wx.VERTICAL)
        self.lbl_sag = wx.StaticText(self, label=dil.get("lbl_content")) 
        right.Add(self.lbl_sag, 0, wx.ALL, 5)
        self.lb_sag = wx.ListBox(self)
        self.lb_sag.Bind(wx.EVT_CONTEXT_MENU, self.menu_sag)
        self.lb_sag.Bind(wx.EVT_KEY_DOWN, self.tus_sag)
        self.lb_sag.Bind(wx.EVT_LISTBOX_DCLICK, self.oynat)
        right.Add(self.lb_sag, 1, wx.EXPAND|wx.ALL, 5)
        btn_oynat = wx.Button(self, label=dil.get("btn_play"))
        btn_oynat.Bind(wx.EVT_BUTTON, self.oynat)
        right.Add(btn_oynat, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(left, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(right, 2, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        self.tazele()

    def tazele(self):
        sec = self.lb_sol.GetStringSelection()
        items = list(self.ana_pencere.playlistler.keys())
        self.lb_sol.Set(items)
        if sec in items: self.lb_sol.SetStringSelection(sec)
        elif items: 
            self.lb_sol.SetSelection(0)
            self.sec_sol(None)

    def sec_sol(self, event):
        ad = self.lb_sol.GetStringSelection()
        if not ad: 
            self.lb_sag.Clear()
            return
        vids = self.ana_pencere.playlistler.get(ad, [])
        self.lb_sag.Set([f"{v['title']}" for v in vids])
        self.lbl_sag.SetLabel(f"{ad} ({len(vids)})")

    def yeni(self, e):
        dlg = wx.TextEntryDialog(self, dil.get("input_list_name"), dil.get("btn_new"))
        if dlg.ShowModal() == wx.ID_OK:
            ad = dlg.GetValue().strip()
            if ad:
                if ad not in self.ana_pencere.playlistler: self.ana_pencere.playlistler[ad] = []
                self.tazele()
        dlg.Destroy()

    def menu_sol(self, e):
        if self.lb_sol.GetSelection() == wx.NOT_FOUND: return
        m = wx.Menu()
        m.Append(1, dil.get("ctx_rename"))
        m.Append(2, dil.get("ctx_delete"))
        m.Append(3, dil.get("ctx_export"))
        self.Bind(wx.EVT_MENU, self.ad_degis, id=1)
        self.Bind(wx.EVT_MENU, self.sil_liste, id=2)
        self.Bind(wx.EVT_MENU, self.m3u, id=3)
        self.PopupMenu(m)
        m.Destroy()

    def tus_sol(self, e):
        k = e.GetKeyCode()
        if k==wx.WXK_F2: self.ad_degis(None)
        elif k==wx.WXK_DELETE: self.sil_liste(None)
        else: e.Skip()

    def ad_degis(self, e):
        sel = self.lb_sol.GetSelection()
        eski = self.lb_sol.GetString(sel)
        dlg = wx.TextEntryDialog(self, "Yeni:", value=eski)
        if dlg.ShowModal() == wx.ID_OK:
            yeni = dlg.GetValue().strip()
            if yeni and yeni!=eski:
                self.ana_pencere.playlistler[yeni] = self.ana_pencere.playlistler.pop(eski)
                playlistleri_kaydet(self.ana_pencere.playlistler)
                self.tazele()
                self.lb_sol.SetStringSelection(yeni)
        dlg.Destroy()

    def sil_liste(self, e):
        sel = self.lb_sol.GetSelection()
        ad = self.lb_sol.GetString(sel)
        if wx.MessageBox(dil.get("msg_confirm_delete"), dil.get("title_confirm"), wx.YES_NO | wx.ICON_QUESTION)==wx.YES:
            del self.ana_pencere.playlistler[ad]
            playlistleri_kaydet(self.ana_pencere.playlistler)
            self.tazele()

    def m3u(self, e):
        sel = self.lb_sol.GetSelection()
        ad = self.lb_sol.GetString(sel)
        dlg = wx.FileDialog(self, "Kaydet", wildcard="M3U|*.m3u", defaultFile=ad+".m3u", style=wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            with open(dlg.GetPath(), "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for v in self.ana_pencere.playlistler[ad]:
                    f.write(f"#EXTINF:-1,{v['title']}\n{v['url']}\n")
            ui.message(dil.get("msg_saved"))
        dlg.Destroy()

    def menu_sag(self, e):
        if self.lb_sag.GetSelection()==wx.NOT_FOUND: return
        m = wx.Menu()
        m.Append(1, dil.get("btn_play"))
        m.Append(2, dil.get("ctx_delete"))
        self.Bind(wx.EVT_MENU, self.oynat, id=1)
        self.Bind(wx.EVT_MENU, self.sil_vid, id=2)
        self.PopupMenu(m)
        m.Destroy()

    def tus_sag(self, e):
        k = e.GetKeyCode()
        if k==wx.WXK_DELETE: self.sil_vid(None)
        else: e.Skip()

    def sil_vid(self, e):
        lad = self.lb_sol.GetStringSelection()
        vid = self.lb_sag.GetSelection()
        del self.ana_pencere.playlistler[lad][vid]
        playlistleri_kaydet(self.ana_pencere.playlistler)
        self.sec_sol(None)

    def oynat(self, e):
        lad = self.lb_sol.GetStringSelection()
        vid = self.lb_sag.GetSelection()
        if lad and vid != wx.NOT_FOUND:
            sistemde_ac(self.ana_pencere.playlistler[lad][vid]['url'])

# --- 3. AYARLAR ---
class AyarlarSekmesi(wx.Panel):
    def __init__(self, parent, ana_pencere):
        super().__init__(parent)
        self.ana_pencere = ana_pencere
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Dil
        sizer.Add(wx.StaticText(self, label="Dil / Language:"), 0, wx.TOP|wx.LEFT, 10)
        self.diller = ["auto"]
        if os.path.exists(lang_path):
            self.diller += [f.replace(".json","") for f in os.listdir(lang_path) if f.endswith(".json")]
        self.ch_lang = wx.Choice(self, choices=self.diller)
        curr = self.ana_pencere.mevcut_ayarlar.get("dil", "auto")
        if curr in self.diller: self.ch_lang.SetSelection(self.diller.index(curr))
        else: self.ch_lang.SetSelection(0)
        sizer.Add(self.ch_lang, 0, wx.EXPAND|wx.ALL, 10)
        
        # Güncelleme
        self.cb_update = wx.CheckBox(self, label=dil.get("chk_auto_update"))
        self.cb_update.SetValue(self.ana_pencere.mevcut_ayarlar.get("otomatik_guncelleme", True))
        sizer.Add(self.cb_update, 0, wx.EXPAND|wx.ALL, 10)
        self.btn_check_update = wx.Button(self, label=dil.get("btn_check_now"))
        self.btn_check_update.Bind(wx.EVT_BUTTON, self.guncelleme_kontrol_btn)
        sizer.Add(self.btn_check_update, 0, wx.ALL, 10)

        # Klasör
        sizer.Add(wx.StaticText(self, label=dil.get("lbl_folder")), 0, wx.TOP|wx.LEFT, 10)
        self.picker = wx.DirPickerCtrl(self, path=self.ana_pencere.mevcut_ayarlar["indirme_klasoru"])
        sizer.Add(self.picker, 0, wx.EXPAND|wx.ALL, 10)
        
        # Kalite Ayarları
        box_kalite = wx.StaticBoxSizer(wx.VERTICAL, self, dil.get("tab_settings"))
        box_kalite.Add(wx.StaticText(self, label=dil.get("lbl_video_quality")), 0, wx.TOP, 5)
        self.ch_video = wx.Choice(self, choices=[dil.get("val_best"), "1080p", "720p", "480p"])
        self.ch_video.SetSelection(self.ana_pencere.mevcut_ayarlar.get("video_kalitesi_idx", 0))
        box_kalite.Add(self.ch_video, 0, wx.EXPAND|wx.ALL, 5)
        
        box_kalite.Add(wx.StaticText(self, label=dil.get("lbl_audio_quality")), 0, wx.TOP, 5)
        self.ch_ses = wx.Choice(self, choices=[dil.get("val_high")+" (320)", dil.get("val_std")+" (192)", dil.get("val_low")+" (128)"])
        self.ch_ses.SetSelection(self.ana_pencere.mevcut_ayarlar.get("ses_kalitesi_idx", 1))
        box_kalite.Add(self.ch_ses, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(box_kalite, 0, wx.EXPAND|wx.ALL, 10)

        # Arama Limiti
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(wx.StaticText(self, label=dil.get("lbl_limit")), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        self.spin = wx.SpinCtrl(self, min=1, max=50, initial=self.ana_pencere.mevcut_ayarlar["arama_sonuc_sayisi"])
        h_sizer.Add(self.spin, 0)
        sizer.Add(h_sizer, 0, wx.ALL, 10)
        
        # --- SES CİHAZI SEÇİMİ (YENİ) ---
        sizer.Add(wx.StaticText(self, label=dil.get("lbl_device")), 0, wx.TOP|wx.LEFT, 10)
        self.cihazlar = self.ana_pencere.player_engine.get_audio_devices()
        cihaz_isimleri = [c[1] for c in self.cihazlar]
        self.choice_device = wx.Choice(self, choices=cihaz_isimleri)
        
        # Mevcut cihazı seç
        mevcut_id = self.ana_pencere.player_engine.device_id
        idx = 0
        for i, dev in enumerate(self.cihazlar):
            if dev[0] == mevcut_id:
                idx = i
                break
        self.choice_device.SetSelection(idx)
        self.choice_device.Bind(wx.EVT_CHOICE, self.on_device_change)
        sizer.Add(self.choice_device, 0, wx.EXPAND|wx.ALL, 10)
        # --------------------------------
        
        btn_kaydet = wx.Button(self, label=dil.get("btn_save"))
        btn_kaydet.Bind(wx.EVT_BUTTON, self.kaydet)
        sizer.Add(btn_kaydet, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        self.SetSizer(sizer)
        
    def guncelleme_kontrol_btn(self, event):
        update_manager.kontrol_et(sessiz=False)

    def on_device_change(self, event):
        sel = self.choice_device.GetSelection()
        if sel != wx.NOT_FOUND:
            dev_id = self.cihazlar[sel][0]
            self.ana_pencere.player_engine.init_device(dev_id)

    def kaydet(self, event):
        eski_dil = self.ana_pencere.mevcut_ayarlar.get("dil", "auto")
        
        # Seçili cihaz ID'sini al
        sel = self.choice_device.GetSelection()
        dev_id = self.cihazlar[sel][0] if sel != wx.NOT_FOUND else -1
        
        yeni = {
            "indirme_klasoru": self.picker.GetPath(),
            "arama_sonuc_sayisi": self.spin.GetValue(),
            "video_kalitesi_idx": self.ch_video.GetSelection(),
            "ses_kalitesi_idx": self.ch_ses.GetSelection(),
            "dil": self.diller[self.ch_lang.GetSelection()],
            "otomatik_guncelleme": self.cb_update.GetValue(),
            "ses_cihazi": dev_id
        }
        ayarlari_kaydet(yeni)
        self.ana_pencere.mevcut_ayarlar = yeni
        
        if eski_dil != yeni["dil"]:
            wx.CallAfter(self.ana_pencere.plugin_instance.arayuzu_yenile)
        else:
            wx.MessageBox(dil.get("msg_saved"), dil.get("title_main"))

# --- İNDİRME MANTIĞI ---
def indirme_baslatici(pencere, url, baslik, format_override=0):
    ayarlar = pencere.mevcut_ayarlar
    fmt_kodu = format_override
    tip_str = "MP3" if fmt_kodu == 1 else "MP4"
    ui.message(f"{dil.get('msg_download_started')}: {baslik} ({tip_str})")
    with indirme_kilidi:
        aktif_indirmeler[url] = {"status": dil.get("msg_download_started"), "cancel": False, "title": baslik}
    threading.Thread(target=arka_plan_indir, args=(url, ayarlar, fmt_kodu, baslik)).start()

def progress_hook(d):
    url = d.get('info_dict', {}).get('webpage_url') or d.get('info_dict', {}).get('original_url')
    if not url: return
    with indirme_kilidi: pass 
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '')
        s = d.get('_speed_str', '')
        msg = f"{dil.get('msg_downloading')}: {p} - {s}"
        with indirme_kilidi:
            for k in aktif_indirmeler:
                if k in url or (d.get('info_dict') and d['info_dict'].get('id') in k):
                    if aktif_indirmeler[k]['cancel']: raise Exception("UserCancel")
                    aktif_indirmeler[k]['status'] = msg

def arka_plan_indir(url, ayarlar, fmt_kodu, baslik):
    try:
        klasor = ayarlar["indirme_klasoru"]
        try:
            if not os.path.exists(klasor): os.makedirs(klasor)
        except:
            klasor = varsayilan_ayarlar["indirme_klasoru"]
            if not os.path.exists(klasor): os.makedirs(klasor)

        if ffmpeg_klasoru not in os.environ["PATH"]: os.environ["PATH"] += os.pathsep + ffmpeg_klasoru
        if not os.path.exists(ffmpeg_exe): raise Exception(dil.get("err_ffmpeg"))
        vid_idx = ayarlar.get("video_kalitesi_idx", 0)
        ses_idx = ayarlar.get("ses_kalitesi_idx", 1)
        vid_height = VIDEO_KALITE_MAP[vid_idx]
        ses_bitrate = SES_KALITE_MAP[ses_idx]
        yol = os.path.join(klasor, "%(title)s.%(ext)s")
        opts = {
            'outtmpl': yol, 'noplaylist': True, 'restrictfilenames': True,
            'nocheckcertificate': True, 'ignoreerrors': True, 'quiet': True,
            'progress_hooks': [progress_hook]
        }
        if fmt_kodu == 1: 
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': ses_bitrate,
                }],
            })
        else: 
            if vid_height is None:
                format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                format_str = f'bestvideo[height<={vid_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={vid_height}][ext=mp4]/best'
            opts['format'] = format_str

        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
        wx.CallAfter(ui.message, f"{dil.get('msg_completed')}: {baslik}")
    except Exception as e:
        if "UserCancel" in str(e): wx.CallAfter(ui.message, dil.get("msg_cancelled"))
        else: 
            log.error(f"Err: {e}")
            wx.CallAfter(ui.message, dil.get("msg_error"))
    finally:
        with indirme_kilidi:
            if url in aktif_indirmeler: del aktif_indirmeler[url]