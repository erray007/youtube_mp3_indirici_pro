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
import languageHandler
import gui
import ui
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

# --- AYARLAR (ÖNCE TANIMLANMALI) ---
varsayilan_ayarlar = {
    "indirme_klasoru": os.path.join(os.path.expanduser("~"), "Downloads"),
    "arama_sonuc_sayisi": 15,
    "video_kalitesi_idx": 0, 
    "ses_kalitesi_idx": 1,
    "dil": "auto" # Yeni: Dil ayarı
}

def ayarlari_yukle():
    ayarlar = varsayilan_ayarlar.copy()
    if os.path.exists(config_dosyasi):
        try:
            with open(config_dosyasi, "r", encoding="utf-8") as f:
                ayarlar.update(json.load(f))
        except: pass
    if not os.path.exists(ayarlar["indirme_klasoru"]):
        ayarlar["indirme_klasoru"] = varsayilan_ayarlar["indirme_klasoru"]
    return ayarlar

def ayarlari_kaydet(ayarlar):
    try:
        with open(config_dosyasi, "w", encoding="utf-8") as f:
            json.dump(ayarlar, f, indent=4)
    except: pass

# --- DİL YÖNETİCİSİ (GÜNCELLENDİ) ---
class DilYoneticisi:
    def __init__(self):
        self.sozluk = {}
        self.varsayilan_yukle()
        # Başlangıçta config'den oku
        conf = ayarlari_yukle()
        self.dil_yukle(conf.get("dil", "auto"))
        
    def varsayilan_yukle(self):
        # Yedek Türkçe (Dosya silinirse çökmesin diye)
        self.sozluk = {
            "menu_name": "YouTube Pro İndirici",
            "title_main": "YouTube Pro İndirici",
            "btn_close": "Kapat",
            "err_title": "Hata",
            "msg_saved": "Ayarlar kaydedildi. Geçerli olması için pencereyi kapatıp açın."
        }

    def dil_yukle(self, secim="auto"):
        try:
            self.varsayilan_yukle() # Önce sıfırla
            
            hedef_kod = "tr" # Varsayılan
            
            if secim == "auto":
                # Sistem dilini al
                hedef_kod = languageHandler.getLanguage().split('_')[0]
            else:
                # Kullanıcı seçimini al
                hedef_kod = secim
            
            # Dosya yolu: languages/en.json vs.
            target_file = os.path.join(lang_path, f"{hedef_kod}.json")
            
            # Bulamazsa tr.json dene
            if not os.path.exists(target_file):
                target_file = os.path.join(lang_path, "tr.json")
            
            if os.path.exists(target_file):
                with open(target_file, "r", encoding="utf-8") as f:
                    veri = json.load(f)
                    self.sozluk.update(veri)
        except Exception as e:
            log.error(f"Dil yükleme hatası: {e}")

    def get(self, key):
        return self.sozluk.get(key, key)

# Global Dil Nesnesi
dil = DilYoneticisi()

# --- DURUM TAKİBİ ---
aktif_indirmeler = {}
indirme_kilidi = threading.Lock()

# Kalite Haritaları
VIDEO_KALITE_MAP = [None, 1080, 720, 480] 
SES_KALITE_MAP = ["320", "192", "128"]

def playlistleri_yukle():
    if os.path.exists(playlist_dosyasi):
        try:
            with open(playlist_dosyasi, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def playlistleri_kaydet(data):
    try:
        with open(playlist_dosyasi, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

# --- YARDIMCI FONKSİYONLAR ---
def sistemde_ac(url):
    try:
        if sys.platform == 'win32': os.startfile(url)
        else: subprocess.Popen(['xdg-open', url])
    except Exception as e: wx.MessageBox(str(e), dil.get("err_title"))

def tarayicida_ac(url):
    webbrowser.open(url)

# --- GLOBAL PLUGIN ---
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super().__init__()
        self.menu_item = gui.mainFrame.sysTrayIcon.toolsMenu.Append(
            wx.ID_ANY, dil.get("menu_name"), dil.get("menu_desc")
        )
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.on_menu_click, self.menu_item)

    def on_menu_click(self, event):
        self.script_arayuzuAc(None)

    def script_arayuzuAc(self, gesture):
        # Her açılışta dili güncelle (Ayarlar değişmiş olabilir)
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
        self.pencere = AnaPencere()

    def terminate(self):
        try: gui.mainFrame.sysTrayIcon.toolsMenu.RemoveItem(self.menu_item)
        except: pass
        super().terminate()

# --- ARAYÜZ ---
class AnaPencere(wx.Frame):
    def __init__(self):
        super().__init__(parent=gui.mainFrame, title=dil.get("title_main"), size=(700, 600))
        self.mevcut_ayarlar = ayarlari_yukle()
        self.playlistler = playlistleri_yukle()
        
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
        except Exception as e:
            wx.CallAfter(self.hata, str(e))

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
        except Exception as e:
            wx.CallAfter(self.hata, str(e))

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
        
        self.Bind(wx.EVT_MENU, lambda e: sistemde_ac(url), id=1)
        self.Bind(wx.EVT_MENU, lambda e: tarayicida_ac(url), id=2)
        self.Bind(wx.EVT_MENU, lambda e: indirme_baslatici(self.ana_pencere, url, baslik, 0), id=3)
        self.Bind(wx.EVT_MENU, lambda e: indirme_baslatici(self.ana_pencere, url, baslik, 1), id=4)
        self.Bind(wx.EVT_MENU, lambda e: self.yeni_pl(sel), id=5)
        for i, pl in enumerate(self.ana_pencere.playlistler.keys()):
            self.Bind(wx.EVT_MENU, lambda e, name=pl, idx=sel: self.ekle_pl(name, idx), id=100+i)
        self.PopupMenu(menu)
        menu.Destroy()

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
            if ad and ad not in self.ana_pencere.playlistler:
                self.ana_pencere.playlistler[ad] = []
                playlistleri_kaydet(self.ana_pencere.playlistler)
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
        if wx.MessageBox(dil.get("msg_confirm_delete"), dil.get("err_title"), wx.YES_NO)==wx.YES:
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

# --- 3. AYARLAR (DİL SEÇENEĞİ EKLENDİ) ---
class AyarlarSekmesi(wx.Panel):
    def __init__(self, parent, ana_pencere):
        super().__init__(parent)
        self.ana_pencere = ana_pencere
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Dil Seçimi (Languages klasörünü tara)
        sizer.Add(wx.StaticText(self, label="Dil / Language:"), 0, wx.TOP|wx.LEFT, 10)
        self.diller = ["auto"]
        if os.path.exists(lang_path):
            self.diller += [f.replace(".json","") for f in os.listdir(lang_path) if f.endswith(".json")]
        
        self.ch_lang = wx.Choice(self, choices=self.diller)
        # Mevcut seçimi bul
        curr = self.ana_pencere.mevcut_ayarlar.get("dil", "auto")
        if curr in self.diller: self.ch_lang.SetSelection(self.diller.index(curr))
        else: self.ch_lang.SetSelection(0)
        sizer.Add(self.ch_lang, 0, wx.EXPAND|wx.ALL, 10)

        # Klasör
        sizer.Add(wx.StaticText(self, label=dil.get("lbl_folder")), 0, wx.TOP|wx.LEFT, 10)
        self.picker = wx.DirPickerCtrl(self, path=self.ana_pencere.mevcut_ayarlar["indirme_klasoru"])
        sizer.Add(self.picker, 0, wx.EXPAND|wx.ALL, 10)
        
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

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(wx.StaticText(self, label=dil.get("lbl_limit")), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        self.spin = wx.SpinCtrl(self, min=1, max=50, initial=self.ana_pencere.mevcut_ayarlar["arama_sonuc_sayisi"])
        h_sizer.Add(self.spin, 0)
        sizer.Add(h_sizer, 0, wx.ALL, 10)
        
        btn_kaydet = wx.Button(self, label=dil.get("btn_save"))
        btn_kaydet.Bind(wx.EVT_BUTTON, self.kaydet)
        sizer.Add(btn_kaydet, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        self.SetSizer(sizer)
        
    def kaydet(self, event):
        yeni = {
            "indirme_klasoru": self.picker.GetPath(),
            "arama_sonuc_sayisi": self.spin.GetValue(),
            "video_kalitesi_idx": self.ch_video.GetSelection(),
            "ses_kalitesi_idx": self.ch_ses.GetSelection(),
            "dil": self.diller[self.ch_lang.GetSelection()]
        }
        ayarlari_kaydet(yeni)
        self.ana_pencere.mevcut_ayarlar = yeni
        
        # Kullanıcıya dil değişikliği için uyarı ver
        if yeni["dil"] != dil.get("lbl_lists"): # Basit bir kontrol, mesajı her türlü verelim
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
        
        if fmt_kodu == 1: # MP3
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': ses_bitrate,
                }],
            })
        else: # MP4
            if vid_height is None:
                format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                format_str = f'bestvideo[height<={vid_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={vid_height}][ext=mp4]/best'
            opts['format'] = format_str

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        wx.CallAfter(ui.message, f"{dil.get('msg_completed')}: {baslik}")
    except Exception as e:
        if "UserCancel" in str(e): wx.CallAfter(ui.message, dil.get("msg_cancelled"))
        else: 
            log.error(f"Err: {e}")
            wx.CallAfter(ui.message, dil.get("msg_error"))
    finally:
        with indirme_kilidi:
            if url in aktif_indirmeler: del aktif_indirmeler[url]