import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ctypes import windll # Používa sa na nastavenie DPI pre lepšie zobrazenie na Windows
import os
import sys
import numpy as np
from scipy.constants import sigma # Stefan-Boltzmannova konštanta pre výpočet žiarenia
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends import backend_svg, backend_pdf
import json

# Importovanie backend logiky z ostatných súborov
# Tieto moduly obsahujú hlavné výpočty a dátové štruktúry pre tepelnú analýzu.
from bar import Bar # Reprezentuje jeden tepelný segment (tyč)
from bar_series import Series # Spravuje sériu prepojených segmentov a vykonáva celkovú analýzu

from calculator import GeometryCalculatorWindow
from graph import GraphWindow, plot

class ThermalApp(tk.Tk):
    """
    Hlavná trieda pre grafické užívateľské rozhranie (GUI) aplikácie tepelnej analýzy.
    Spravuje okno aplikácie, užívateľské vstupy, spúšťanie analýzy a zobrazovanie výsledkov.
    """
    def __init__(self):
        """
        Inicializuje hlavné okno aplikácie a jeho komponenty.
        Nastavuje titulok, predvolenú veľkosť okna a inicializuje interné dátové štruktúry.
        """

        super().__init__()
        self.title("BarSerNew") # Titulok okna aplikácie
        self.geometry(f"{int(2/3*self.winfo_screenwidth()//1)}x{int(2/3*self.winfo_screenheight()//1)}") # Počiatočné rozmery okna
        self.state('zoomed') # Aplikácia sa spustí maximalizovaná

        # Zistite, či aplikácia beží ako balík PyInstaller
        if getattr(sys, 'frozen', False):
            # Ak je aplikácia zmrazená (balená PyInstallerom), cesta k dátovým súborom je v sys._MEIPASS
            application_path = sys._MEIPASS
        else:
            # Ak aplikácia beží ako normálny skript Pythonu, cesta je aktuálny pracovný adresár
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.icon_path = os.path.join(application_path, "ikonka.png")
        image = Image.open(self.icon_path)
        photo = ImageTk.PhotoImage(image)
        self.wm_iconphoto(True, photo)

        # Zoznamy na uloženie referencií na GUI rámce pre jednotlivé segmenty a uzly.
        self.bar_frames = [] # Ukladá LabelFrames pre tepelné segmenty (tyče)
        self.node_frames = [] # Ukladá LabelFrames pre medziľahlé uzly medzi segmentmi

        self.series = None # Bude obsahovať objekt BarSeries po úspešnej analýze
        self.figure = None # Bude obsahovať Matplotlib figúru pre vykreslenie grafu výsledkov

        # Nová StringVar pre cestu k adresáru TCD
        self.tcd_dir_path = tk.StringVar(value=os.path.join(os.getcwd(), "TCD")) # Predvolená hodnota je podadresár 'TCD' v aktuálnom pracovnom adresári

        self._create_widgets() # Volá metódu na vytvorenie GUI elementov
        self._redirect_stdout() # Presmeruje výstupy print() do konzoly v GUI
        
        self.add_bar_frame() # Pridá prvý predvolený segment pri spustení aplikácie
        print("[INFO] Vitajte v BarSerNew. Definujte okrajové podmienky a pridajte segmenty.")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _create_widgets(self):
        """
        Vytvára a usporadúva všetky hlavné widgety a definuje rozloženie aplikácie.
        Zahŕňa vstupné panely, výstupné panely, ovládacie tlačidlá a konzolový záznam.
        """
        # Hlavné panelové okno pre vertikálne oddelenie (vstupy/výstupy vs. konzola)
        main_paned_window = tk.PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5, bg = "#DFDFDF", bd = 0)
        main_paned_window.pack(fill=tk.BOTH, expand=True)
        main_paned_window.configure(opaqueresize=False)

        # Horný rámec obsahujúci vstupné a výstupné panely a ovládacie tlačidlá
        top_frame = tk.Frame(main_paned_window)
        main_paned_window.add(top_frame)

        # --- Ovládacie tlačidlá ---
        button_frame = ttk.Frame(top_frame, padding=5)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Tlačidlá pre interakciu s užívateľom
        self.btn_load_project = ttk.Button(button_frame, text="Načítať Projekt", command=self.load_project)
        self.btn_load_project.pack(side=tk.LEFT, padx=5)

        self.btn_save_project = ttk.Button(button_frame, text="Uložiť Projekt", command=self.save_project)
        self.btn_save_project.pack(side=tk.LEFT, padx=5)

        self.btn_add_bar = ttk.Button(button_frame, text="Pridať segment", command=self.add_bar_frame)
        self.btn_add_bar.pack(side=tk.LEFT, padx=5)
        
        self.btn_run = ttk.Button(button_frame, text="Spustiť Analýzu", style="Accent.TButton", command=self.run_analysis)
        self.btn_run.pack(side=tk.LEFT, padx=5)
        
        self.btn_reset = ttk.Button(button_frame, text="Resetovať Všetko", command=self.reset_ui)
        self.btn_reset.pack(side=tk.RIGHT, padx=5)

        self.btn_save_data = ttk.Button(button_frame, text="Uložiť Dáta", state="disabled", command=self.save_data_to_file)
        self.btn_save_data.pack(side=tk.RIGHT, padx=5)

        self.btn_save_plot = ttk.Button(button_frame, text="Uložiť Graf", state="disabled", command=self.save_plot)
        self.btn_save_plot.pack(side=tk.RIGHT, padx=5)

        self.btn_plot = ttk.Button(button_frame, text="Vykresliť Graf", state="disabled", command=self.plot_results)
        self.btn_plot.pack(side=tk.RIGHT, padx=5)

        # Panelové okno v rámci horného rámca pre horizontálne oddelenie (vstupy vs. výstupy)
        top_paned_window = tk.PanedWindow(top_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        top_paned_window.pack(fill=tk.BOTH, expand=True)
        main_paned_window.add(top_frame)

        # --- 1. Ľavý panel (Vstupy) ---
        input_panel = ttk.Frame(top_paned_window, padding=(10, 0))
        top_paned_window.add(input_panel, width=int(11/30*self.winfo_screenwidth()//1)) # Nastavuje počiatočnú šírku pre vstupný panel

        # Nová sekcia pre výber adresára TCD
        tcd_dir_frame = ttk.LabelFrame(input_panel, text=" Adresár súborov s tabuľkami tepelnej vodivosti ", padding=10)
        tcd_dir_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        tcd_dir_frame.columnconfigure(1, weight=1)

        ttk.Label(tcd_dir_frame, text="Cesta k adresáru:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(tcd_dir_frame, textvariable=self.tcd_dir_path, state="readonly").grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        ttk.Button(tcd_dir_frame, text="Vybrať Adresár", command=self._browse_tcd_directory).grid(row=0, column=2, sticky="e", padx=5, pady=2)
        
        # LabelFrame pre globálne okrajové podmienky, umiestnený v hornej časti vstupného panela
        global_bc_frame = ttk.LabelFrame(input_panel, text=" Globálne okrajové podmienky ", padding=10)
        global_bc_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        
        # Konfiguruje stĺpce pre rámec globálnych okrajových podmienok, aby sa Entry widgety mohli rozširovať
        global_bc_frame.columnconfigure(1, weight=1) 
        global_bc_frame.columnconfigure(3, weight=1)

        # Tkinter StringVars na uloženie globálnych hraničných teplôt
        self.T0_global = tk.StringVar(value="77.0") # Teplota na začiatku (x=0) celej série
        self.TL_global = tk.StringVar(value="4.2")   # Teplota na konci (x=L) celej série

        # Popisky a Entry widgety pre vstupy globálnych teplôt
        ttk.Label(global_bc_frame, text="Teplota začiatok T(x=0) [K]:").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Entry(global_bc_frame, textvariable=self.T0_global).grid(row=0, column=1, sticky="ew", padx=5) 
        
        ttk.Label(global_bc_frame, text="Teplota koniec T(x=L) [K]:").grid(row=0, column=2, sticky="w", padx=5)
        ttk.Entry(global_bc_frame, textvariable=self.TL_global).grid(row=0, column=3, sticky="ew", padx=5)

        # Oddeľovač pre vizuálne rozlíšenie
        ttk.Separator(input_panel, orient='horizontal').pack(fill='x', pady=5, padx=5)

        # Kontajner pre dynamicky pridávané tepelné segmenty a uzly
        segments_container = ttk.Frame(input_panel)
        segments_container.pack(fill=tk.BOTH, expand=True)

        # Canvas a posuvník pre vstupnú oblasť, aby bolo možné rolovať, keď je pridaných veľa segmentov
        self.input_canvas = tk.Canvas(segments_container, borderwidth=0, highlightthickness=0)
        self.input_scrollbar = ttk.Scrollbar(segments_container, orient="vertical", command=self.input_canvas.yview)
        # Rámec vo vnútri canvasu, kam sú umiestnené vstupné widgety segmentov a uzlov
        self.scrollable_input_frame = ttk.Frame(self.input_canvas, padding=(0, 0, 15, 0)) # Padding pre scrollbar
        # Pri zmene veľkosti vnútorného rámca, aktualizujte scrollregion canvasu
        self.scrollable_input_frame.bind("<Configure>", lambda e: self.input_canvas.configure(scrollregion=self.input_canvas.bbox("all")))
        self.input_canvas.create_window((0, 0), window=self.scrollable_input_frame, anchor="nw")
        self.input_canvas.configure(yscrollcommand=self.input_scrollbar.set)
        
        self.input_canvas.pack(side="left", fill="both", expand=True)
        self.input_scrollbar.pack(side="right", fill="y")
        
        # --- 2. Pravý panel (Výstupy) ---
        output_canvas_frame = ttk.Frame(top_paned_window, padding=10)
        top_paned_window.add(output_canvas_frame) # Nastavuje počiatočnú šírku pre výstupný panel
        ttk.Label(output_canvas_frame, text="Výsledky Analýzy", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        # Canvas a posuvník pre zobrazovanie výsledkov analýzy
        self.output_canvas = tk.Canvas(output_canvas_frame, borderwidth=0, highlightthickness=0)
        self.output_scrollbar = ttk.Scrollbar(output_canvas_frame, orient="vertical", command=self.output_canvas.yview)
        self.scrollable_output_frame = ttk.Frame(self.output_canvas, padding=(0, 0, 15, 0))
        self.scrollable_output_frame.bind("<Configure>", lambda e: self.output_canvas.configure(scrollregion=self.output_canvas.bbox("all")))
        self.output_canvas.create_window((0, 0), window=self.scrollable_output_frame, anchor="nw")
        self.output_canvas.configure(yscrollcommand=self.output_scrollbar.set)
        self.output_canvas.pack(side="left", fill="both", expand=True)
        self.output_scrollbar.pack(side="right", fill="y")

        # --- Dolný panel (Konzolový výstup) ---
        log_frame = ttk.Frame(main_paned_window, padding=10)
        main_paned_window.add(log_frame)
        ttk.Label(log_frame, text="Správy Programu", font=("Helvetica", 12)).pack(anchor="w")
        
        # Textový widget pre zobrazovanie programových správ a chýb (presmerovaný stdout/stderr)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word", font=("Courier New", 10), borderwidth=0)
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Počiatočné nastavenie pozície deliča v hlavnom PanedWindow
        # Aktualizujte widgety, aby sa zabezpečilo, že majú rozmery
        self.update_idletasks() 
        # Nastaví horný panel na približne 4/5 výšky okna a spodný (konzola) na 1/5
        sash_position = int(self.winfo_height() * 4/5)
        main_paned_window.sash_place(0, 0, sash_position) # 0 je index prepážky (prvá prepážka)

    def _redirect_stdout(self):
        """
        Presmeruje štandardný výstup (príkazy print) a štandardnú chybu do
        textového widgetu v GUI, čo umožňuje užívateľom vidieť správy programu priamo
        v aplikácii.
        """
        class StdoutRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget
            def write(self, string):
                self.text_widget.config(state="normal")  # Povoliť zápis do textového widgetu
                self.text_widget.insert("end", string)   # Vložiť reťazec na koniec
                self.text_widget.see("end")              # Posunúť na koniec pre zobrazenie najnovších správ
                self.text_widget.config(state="disabled") # Zakázať úpravy užívateľom
            def flush(self):
                pass # Vyžadované pre objekty podobné súborom, ale tu sa nepoužíva

        sys.stdout = StdoutRedirector(self.log_text)
        sys.stderr = StdoutRedirector(self.log_text)

    def _browse_tcd_directory(self):
        """
        Otvorí dialógové okno pre výber adresára a uloží vybranú cestu do self.tcd_dir_path.
        Následne aktualizuje Comboboxy s materiálmi.
        """
        directory = filedialog.askdirectory(title="Vybrať Adresár pre .TCD súbory")
        if directory:
            self.tcd_dir_path.set(directory)
            print(f"[INFO] Adresár .TCD súborov nastavený na: {directory}")
            self._update_material_comboboxes() # Aktualizovať zoznam súborov v Comboboxoch

    def _get_tcd_files(self):
        """
        Prehľadá adresár určený v self.tcd_dir_path pre súbory vlastností materiálov (prípona .TCD).
        Tieto súbory obsahujú údaje o tepelnej vodivosti pre rôzne materiály.
        Vráti zoznam nájdených názvov súborov alebo informačnú správu, ak sa žiadne nenájdu, alebo nastane chyba.
        """
        try:
            tcd_dir = self.tcd_dir_path.get()
            if not os.path.isdir(tcd_dir):
                return [f"Adresár nenájdený."]
            files = [f for f in os.listdir(tcd_dir) if (f.endswith(".TCD") or f.endswith(".tcd"))] # Filtruje len .TCD súbory
            return files if files else ["Žiadne .TCD súbory"]
        except Exception as e:
            return [f"Chyba pri čítaní adresára: {e}"]

    def _update_material_comboboxes(self):
        """
        Aktualizuje zoznam hodnôt v Comboboxoch pre výber materiálu vo všetkých segmentoch.
        Táto metóda sa volá po zmene adresára TCD.
        """
        tcd_files = self._get_tcd_files()
        for frame in self.bar_frames:
            if "Materiál" in frame.entries:
                material_var = frame.entries["Materiál"]
                # Nájdeme Combobox priradený k 'Materiál' StringVare
                for child in frame.winfo_children():
                    if isinstance(child, ttk.Combobox) and child.cget("textvariable") == str(material_var):
                        child['values'] = tcd_files
                        if tcd_files and material_var.get() not in tcd_files:
                            material_var.set(tcd_files[0]) # Nastaví prvú dostupnú hodnotu, ak aktuálna nie je platná
                        elif not tcd_files:
                            material_var.set("") # Vyprázdni, ak žiadne súbory nie sú k dispozícii
                        break

    def _open_geometry_calculator(self, entries_to_update):
        """
        Otvorí nové okno s kalkulačkou geometrie pre daný segment.

        Args:
            entries_to_update (dict): Slovník s Tkinter premennými, ktoré má kalkulačka aktualizovať.
        """
        # Vytvorí inštanciu našej novej triedy okna
        calculator_window = GeometryCalculatorWindow(self, entries_to_update)
        
    def add_bar_frame(self):
        """
        Pridá nový vstupný rámec pre tepelný segment (tyč) a, ak je to potrebné,
        vstupný rámec pre medzilehlý uzol do rolovacej vstupnej oblasti.
        Každý segment umožňuje definovať jeho vlastnosti (dĺžka, plocha, materiál atď.).
        Uzly umožňujú definovať externé tepelné toky a odhady teplôt.
        """
        bar_index = len(self.bar_frames) # Určí index pre nový segment (začína od 0)
        
        # Pridaj uzlový rámec len AK to nie je prvý pridávaný segment.
        # Uzly predstavujú rozhrania medzi segmentmi.
        if bar_index > 0:
            node_frame = ttk.LabelFrame(self.scrollable_input_frame, text=f" UZOL {bar_index} ", padding=10)
            node_frame.pack(fill=tk.X, padx=5, pady=5)
            node_frame.columnconfigure(1, weight=1) # Umožniť rozšírenie vstupného widgetu
            
            ttk.Label(node_frame, text="Externý tepelný tok [mW]:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
            node_frame.ext_q = tk.StringVar(value="0.0") # Premenná pre externý tepelný tok v uzle
            ttk.Entry(node_frame, textvariable=node_frame.ext_q).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
            
            ttk.Label(node_frame, text="Odhadovaná teplota [K]:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
            node_frame.temp_guess = tk.StringVar(value="50.0") # Premenná pre počiatočný odhad teploty v uzle
            ttk.Entry(node_frame, textvariable=node_frame.temp_guess).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
            self.node_frames.append(node_frame)

        # Vytvorí LabelFrame pre nový segment
        frame = ttk.LabelFrame(self.scrollable_input_frame, text=f" SEGMENT {bar_index + 1} ", padding=10)
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Konfiguruje stĺpce v rámci segmentu, aby sa vstupným widgetom umožnilo rozšírenie
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.entries = {} # Slovník na uloženie Tkinter StringVars pre parametre segmentu
        
        # Definuje predvolené parametre pre nový segment
        params = {
            "Názov": f"Segment_{bar_index+1}", "Dĺžka [mm]": "100", "Prierez [mm^2]": "1", 
            "Obvod [mm]": "4", "Emisivita [-]": "0.1", # Emisivita
            "Materiál": "", "T okolia [K]": "300"
        }
        
        param_items = list(params.items())
        num_params = len(param_items)
        split_point = (num_params + 1) // 2 # Používa sa na usporiadanie parametrov do dvoch stĺpcov

        # Vytvára popisky a vstupné widgety pre každý parameter segmentu
        for i, (label, value) in enumerate(param_items):
            row, col_offset = (i, 0) if i < split_point else (i - split_point, 2)
            ttk.Label(frame, text=label + ":").grid(row=row, column=col_offset, sticky="w", padx=5, pady=2)
            var = tk.StringVar(value=value)
            frame.entries[label] = var
            
            if label == "Materiál":
                # Pre výber materiálu použije Combobox naplnený .TCD súbormi
                widget = ttk.Combobox(frame, textvariable=var, values=self._get_tcd_files())
                if widget['values']:
                    widget.set(widget['values'][0]) # Nastaví predvolenú hodnotu, ak sa nájdu súbory
                else:
                    widget.set("N/A - Žiadne .TCD súbory")
            else:
                # Pre ostatné parametre použije štandardný Entry widget
                widget = ttk.Entry(frame, textvariable=var)
            widget.grid(row=row, column=col_offset + 1, sticky="ew", padx=(0, 10), pady=2)

        # Pridá tlačidlo "Odstrániť Segment" a "Kalkulačka" priamo do rámca segmentu
        button_frame = ttk.Frame(frame)
        # Umiestni button_frame napravo od parametrov
        button_frame.grid(row=split_point -1, column=2, columnspan=2, sticky="ew", padx=(0, 10), pady=2, ipadx=5)
        # Konfigurácia stĺpcov pre button_frame, aby sa rovnomerne roztiahli
        button_frame.columnconfigure(0, weight=1) # Prvý stĺpec pre calc_button
        button_frame.columnconfigure(1, weight=1) # Druhý stĺpec pre delete_button

        delete_button = ttk.Button(button_frame, text="Odstrániť Segment", command=lambda f=frame: self.remove_bar_frame(f))
        calc_button = ttk.Button(button_frame, text="Kalkulačka", command=lambda e=frame.entries: self._open_geometry_calculator(e))
        # Umiestnenie tlačidiel do gridu s sticky="ew" a bez pady (už je na button_frame)
        calc_button.grid(row=0, column=0, sticky="ew", padx=(0, 2)) # Pridajte malý medzipriestor medzi tlačidlami
        delete_button.grid(row=0, column=1, sticky="ew", padx=(2, 0)) # Pridajte malý medzipriestor


        self.bar_frames.append(frame) # Pridá nový rámec segmentu do zoznamu
        self._update_segment_labels() # Preindexuje a prebalí všetky rámce pre udržanie poradia

    def remove_bar_frame(self, frame_to_remove):
        """
        Odstráni zadaný rámec segmentu a jeho zodpovedajúci uzlový rámec (ak existuje).
        Zabráni odstráneniu, ak zostáva len jeden segment.
        """
        if len(self.bar_frames) == 1:
            messagebox.showwarning("Upozornenie", "Nemôžete odstrániť posledný segment.")
            return

        index_to_remove = self.bar_frames.index(frame_to_remove)
        
        # Zničí GUI rámec pre segment a odstráni ho zo zoznamu
        frame_to_remove.destroy()
        self.bar_frames.pop(index_to_remove)

        # Logika pre odstránenie prislúchajúceho uzla:
        # Ak zostáva len jeden segment, vymaže všetky uzlové rámce (nie sú potrebné medzilehlé uzly).
        # Ak sa odstraňuje segment, odstráni sa uzol PRED ním.
        # (Predpokladá sa, že uzol je vždy pred segmentom, ktorý spája.)
        if len(self.bar_frames) == 1: # Ak zostal len 1 segment, odstráň všetky uzly
            for node_f in self.node_frames:
                node_f.destroy()
            self.node_frames.clear()
        # Ak sa neodstraňuje posledný segment v novom poradí (po popnutí)
        # a existujú uzly, odstráni sa uzol, ktorý bol spojený s týmto segmentom z ľavej strany
        elif len(self.node_frames) > 0 and index_to_remove < len(self.node_frames):
            self.node_frames[index_to_remove].destroy()
            self.node_frames.pop(index_to_remove)
        # Ak bol odstránený posledný segment a existuje posledný uzol, odstráni sa aj ten
        elif len(self.node_frames) > 0 and index_to_remove == len(self.node_frames):
            self.node_frames[-1].destroy()
            self.node_frames.pop()
        
        self._update_segment_labels() # Preindexuje a prebalí rámce pre správne číslovanie
        print(f"[INFO] Segment {index_to_remove + 1} bol odstránený.")

    def _update_segment_labels(self):
        """
        Preusporiada a aktualizuje popisky (napr. "SEGMENT 1", "UZOL 1") všetkých
        LabelFrames segmentov a uzlov po pridaní alebo odstránení.
        Tým sa zabezpečí konzistentné číslovanie a správne vizuálne usporiadanie v rolovacej vstupnej oblasti.
        """
        all_widgets = self.scrollable_input_frame.winfo_children()
        
        # Získa aktuálne referencie na existujúce LabelFrames, rozdelí ich na segmenty a uzly.
        self.bar_frames = [f for f in all_widgets if isinstance(f, ttk.LabelFrame) and "SEGMENT" in f.cget("text")]
        self.node_frames = [f for f in all_widgets if isinstance(f, ttk.LabelFrame) and "UZOL" in f.cget("text")]
        
        # Vytvorí nový, správne usporiadaný zoznam rámcov.
        ordered_frames = []
        current_node_index_in_ordered = 0 # Sleduje index pre uzly
        for i in range(len(self.bar_frames)): # Iteruje podľa počtu segmentov
            if i > 0: # Uzol je vždy pred segmentom, ak to nie je prvý segment
                if current_node_index_in_ordered < len(self.node_frames):
                    ordered_frames.append(self.node_frames[current_node_index_in_ordered])
                    current_node_index_in_ordered += 1
            ordered_frames.append(self.bar_frames[i])

        # Odbalí a potom znova zabalí widgety v správnom poradí, aby sa aplikovali vizuálne zmeny.
        for frame in all_widgets:
            frame.pack_forget()

        current_bar_label_index = 1
        current_node_label_index = 1
        for frame in ordered_frames:
            if "SEGMENT" in frame.cget("text"):
                frame.config(text=f" SEGMENT {current_bar_label_index} ")
                # Aktualizuje príkaz tlačidla na odstránenie, aby odkazovalo na novú, usporiadú referenciu rámca.
                delete_button = next((w for w in frame.winfo_children() if isinstance(w, ttk.Button) and w.cget("text") == "Odstrániť Segment"), None)
                if delete_button:
                    delete_button.config(command=lambda f=frame: self.remove_bar_frame(f))
                current_bar_label_index += 1
            elif "UZOL" in frame.cget("text"):
                frame.config(text=f" UZOL {current_node_label_index} ")
                current_node_label_index += 1
            frame.pack(fill=tk.X, padx=5, pady=5)

        # Uistí sa, že interné zoznamy (self.bar_frames, self.node_frames) sú aktualizované
        # tak, aby odrážali nové usporiadanie rámcov v GUI.
        self.bar_frames = [f for f in self.scrollable_input_frame.winfo_children() if isinstance(f, ttk.LabelFrame) and "SEGMENT" in f.cget("text")]
        self.node_frames = [f for f in self.scrollable_input_frame.winfo_children() if isinstance(f, ttk.LabelFrame) and "UZOL" in f.cget("text")]
        
        # Aktualizuje oblasť posúvania canvasu po prebalení rámcov.
        self.input_canvas.update_idletasks()
        self.input_canvas.config(scrollregion=self.input_canvas.bbox("all"))

    def _validate_float(self, value_str, field_name, segment_name=None):
        """
        Pokúsi sa prekonvertovať reťazec na float. Ak zlyhá, zobrazí chybovú hlášku.
        Vracia float hodnotu alebo None v prípade chyby.
        """
        try:
            value = float(value_str)
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            error_title = "Chybný vstup"
            if segment_name:
                error_message = f"V segmente '{segment_name}' je zadaná neplatná hodnota pre pole '{field_name}'.\nZadajte platné číslo (použite bodku '.' ako desatinný oddeľovač)."
            else:
                error_message = f"V poli '{field_name}' je zadaná neplatná hodnota.\nZadajte platné číslo (použite bodku '.' ako desatinný oddeľovač)."
            
            messagebox.showerror(error_title, error_message)
            print(f"[CHYBA] {error_message}")
            return None

    def run_analysis(self):
        """
        Spustí tepelnú analýzu na základe aktuálne zadaných parametrov.
        Zhromažďuje dáta z vstupných rámcov segmentov a uzlov, vytvorí objekt Series,
        vyrieši tepelný problém a následne zobrazí výsledky v GUI.
        Obsahuje ošetrenie potenciálnych chýb pri zbere dát alebo analýze.
        """
        print("\n" + "=" * 40)
        print("[INFO] Spúšťam analýzu...")
        self.reset_results()
        self.series = None

        try:
            bars = []
            current_tcd_dir = self.tcd_dir_path.get()
            if not os.path.isdir(current_tcd_dir):
                messagebox.showerror("Chyba adresára TCD", f"Zadaný adresár pre .TCD súbory neexistuje: {current_tcd_dir}")
                return

            for i, frame in enumerate(self.bar_frames):
                p = {k: v.get() for k, v in frame.entries.items()}
                
                # --- VALIDÁCIA VSTUPOV PRE SEGMENT ---
                nazov = p["Názov"]
                dlzka_val = self._validate_float(p["Dĺžka [mm]"], "Dĺžka [mm]", nazov)
                prierez_val = self._validate_float(p["Prierez [mm^2]"], "Prierez [mm^2]", nazov)
                obvod_val = self._validate_float(p["Obvod [mm]"], "Obvod [mm]", nazov)
                emisivita_val = self._validate_float(p["Emisivita [-]"], "Emisivita [-]", nazov)
                tokolia_val = self._validate_float(p["T okolia [K]"], "T okolia [K]", nazov)

                # Ak niektorá validácia zlyhala, ukončíme analýzu
                if any(v is None for v in [dlzka_val, prierez_val, obvod_val, emisivita_val, tokolia_val]):
                    print("[CHYBA] Analýza zastavená kvôli neplatným vstupom.")
                    return

                material_file = p["Materiál"]
                if material_file not in self._get_tcd_files():
                    print("[CHYBA] Analýza neúspešná.")
                    messagebox.showerror("Chyba materiálu", f"V segmente '{nazov}' je vybraný neplatný materiál: '{material_file}'.")
                    return

                bar = Bar(
                    nazov=nazov, subor=os.path.join(current_tcd_dir, material_file),
                    L=dlzka_val / 1e3, A=prierez_val / 1e6,
                    P=obvod_val / 1e3, epsilon=emisivita_val,
                    T_okolie=tokolia_val, T0=0, TL=0
                )
                if not bar.correct:
                    raise ValueError(f"Inicializácia segmentu '{bar.nazov}' zlyhala. Skontrolujte vstupy a konzolu.")
                bars.append(bar)

            if not bars:
                messagebox.showwarning("Chýbajú segmenty", "Pridajte aspoň jeden segment pre spustenie analýzy.")
                return

            # --- VALIDÁCIA GLOBÁLNYCH PODMIENOK ---
            T0_global_val = self._validate_float(self.T0_global.get(), "Teplota začiatok T(x=0) [K]")
            TL_global_val = self._validate_float(self.TL_global.get(), "Teplota koniec T(x=L) [K]")
            if T0_global_val is None or TL_global_val is None:
                print("[CHYBA] Analýza zastavená kvôli neplatným globálnym okrajovým podmienkam.")
                return

            bars[0].T0 = T0_global_val
            bars[-1].TL = TL_global_val
            
            ext_q_vals = []
            for i, f in enumerate(self.node_frames):
                q_val = self._validate_float(f.ext_q.get(), f"Externý tepelný tok [mW] (Uzol {i+1})")
                if q_val is None: return
                ext_q_vals.append(q_val / 1e3) # Prevod mW na W

            self.series = Series(bars, ext_q_vals)
            if not self.series.correct:
                return

            if len(bars) > 1:
                temp_guesses_vals = []
                for i, f in enumerate(self.node_frames):
                    guess_val = self._validate_float(f.temp_guess.get(), f"Odhadovaná teplota [K] (Uzol {i+1})")
                    if guess_val is None: return
                    temp_guesses_vals.append(guess_val)
                
                guess = np.array(temp_guesses_vals)
                print(f"[INFO] Používam zadaný počiatočný odhad teplôt na rozhraniach: {guess} K")
                self.series.solve(temp_guess=guess)
            else:
                self.series.solve()

            if self.series.correct:
                self.populate_results()
                self.console_output(self.series)
                self.figure = plot(self.series)
                self.btn_plot.config(state="normal")
                self.btn_save_plot.config(state="normal")
                self.btn_save_data.config(state="normal")
                messagebox.showinfo("Analýza dokončená", "Analýza bola úspešne dokončená.")
            else:
                messagebox.showerror("Chyba pri analýze", "Analýza zlyhala. Skontrolujte vstupné parametre a správy v konzole.")

        except Exception as e:
            messagebox.showerror("Kritická chyba pri analýze", f"Nastala neočakávaná chyba: {e}")
            print(f"[CHYBA] Kritická chyba počas analýzy: {e}")
            
    def console_output(self, series):   
        """
        Vypíše do konzoly súhrnné výsledky analýzy.

        Zobrazí maximálnu teplotu, tepelné toky na okrajoch a skontroluje
        energetickú bilanciu porovnaním rozdielu tokov s celkovým teplom
        vyžiareným do okolia.

        Args:
            series (Series): Objekt `Series` s výsledkami.
        """
        if not series.correct:
            print("[INFO] Výpis výsledkov do konzoly preskočený, pretože analýza nebola úspešná.")
            return

        # Kladný tok Q znamená tok tepla v smere rastúcej súradnice x (zľava doprava).
        Q_zaciatok = series.Q_plot[0]
        Q_koniec = series.Q_plot[-1]

        # --- Energetická bilancia ---
        # Celkové teplo vyžiarené do okolia sa počíta ako integrál strát žiarením
        # pozdĺž celej dĺžky sústavy.
        # P_rad = integral[0, L_total] (epsilon * sigma * P * (T(x)^4 - T_okolie^4)) dx
        Q_vyziarene = 0
        for bar in series.bar_list:
            # Použitie hustejšej siete pre presnejšiu numerickú integráciu
            x_dense = np.linspace(0, bar.L, int(bar.L//1e-5))
            T_dense = bar.riesenie.sol(x_dense)[0]
            # Integrant funkcie pre tepelné straty žiarením
            integrand = bar.epsilon * sigma * bar.P * (T_dense**4 - bar.T_okolie**4)
            # Numerická integrácia pomocou trapezoidového pravidla
            Q_bar = np.trapezoid(integrand, x_dense)
            Q_vyziarene += Q_bar
        
        # Nájdenie maximálnej teploty a jej polohy
        idx_max = np.argmax(series.T_plot)
        T_maximum = series.T_plot[idx_max]
        x_max = series.x_plot[idx_max]

        # Formátovaný výstup
        print("\n"+"="*40)
        print("      VÝSLEDKY ANALÝZY PRE SÚSTAVU")
        print("="*40)

        print(f"Maximálna teplota sústavy: {T_maximum:.2f} K")
        print(f"Poloha maximálnej teploty: x = {x_max*1000:.2f} mm")
        print()
        print(f"Tepelný tok vstupujúci (x=0):   {Q_zaciatok*1000: .3f} mW")
        print(f"Tepelný tok vystupujúci (x=L):  {Q_koniec*1000: .3f} mW")
        print()
        print(f"Žiarivý výkon (sústava->okolie) (numerická integrácia): {Q_vyziarene*1000: .3f} mW")
        print(f"Rozdiel tokov (Q_zaciatok - Q_koniec): {(Q_zaciatok - Q_koniec)*1000: .3f} mW")
        print("="*40)

    def populate_results(self):
        """
        Zobrazí vypočítané výsledky tepelnej analýzy v pravom výstupnom paneli.
        To zahŕňa teploty a tepelné toky na rozhraniach segmentov a podrobné
        výsledky pre každý jednotlivý segment (maximálna teplota, vyžiarený výkon atď.).
        """
        if not self.series or not self.series.correct:
            return # Nerobí nič, ak nie sú k dispozícii platné výsledky analýzy

        cum_L = 0 # Kumulatívna dĺžka na sledovanie polohy pozdĺž celej série
        for i, bar in enumerate(self.series.bar_list):
            if i > 0:
                # Zobrazuje výsledky pre medzilehlé uzly (rozhrania medzi segmentmi)
                res_node_frame = ttk.LabelFrame(self.scrollable_output_frame, text=f" UZOL {i} ", padding=10)
                res_node_frame.pack(fill=tk.X, padx=5, pady=5)
                
                temp = self.series.solution_temps[i-1] # Teplota v aktuálnom uzle
                extQ = self.series.ext_Q[i-1]         # Externý tepelný tok v aktuálnom uzle
                
                ttk.Label(res_node_frame, text=f"Teplota na rozhraní: {temp:.3f} K").pack(anchor="w")
                ttk.Label(res_node_frame, text=f"Externý tepelný tok: {extQ*1e3:.3f} mW").pack(anchor="w") # Prevod W na mW
            
            # Zobrazuje podrobné výsledky pre každý segment
            res_frame = ttk.LabelFrame(self.scrollable_output_frame, text=f" SEGMENT {i+1} ({bar.nazov})", padding=10)
            res_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Vypočíta špecifické výsledky segmentu z celkového riešenia
            start_x, end_x = cum_L, cum_L + bar.L
            seg_indices = np.where((self.series.x_plot >= start_x) & (self.series.x_plot <= end_x))
            
            T_seg, x_seg = self.series.T_plot[seg_indices], self.series.x_plot[seg_indices]
            T_max, x_max_local = np.max(T_seg), x_seg[np.argmax(T_seg)]
            
            Q_start, Q_end = self.series.Q_plot[seg_indices[0][0]], self.series.Q_plot[seg_indices[0][-1]]
            if len(self.series.bar_list) > 1: Q_end -= self.series.ext_Q[i-1] 
            if i == len(self.series.bar_list)-1:
                Q_end = self.series.Q_plot[seg_indices[0][-1]]
            
            # Vypočíta vyžiarený výkon stratený zo segmentu do okolia pomocou numerickej integrácie
            x_dense = np.linspace(0, bar.L, int(bar.L//1e-5)) # Hustejšie body pre presnejšiu integráciu
            T_dense = bar.riesenie.sol(x_dense)[0]
            integrand = bar.epsilon * sigma * bar.P * (T_dense**4 - bar.T_okolie**4)
            Q_rad = np.trapezoid(integrand, x_dense)
            
            # Pripraví slovník výsledkov na zobrazenie
            results = {"Teplota začiatok": f"{bar.T0:.2f} K",
                       "Teplota koniec": f"{bar.TL:.2f} K",
                       "Tepelný tok začiatok": f"{Q_start*1000:.3f} mW",
                       "Tepelný tok koniec": f"{Q_end*1000:.3f} mW",
                       "Rozdiel tokov": f"{Q_start*1000-Q_end*1000:.3f} mW", # Rozdiel tepelných tokov na koncoch segmentu
                       "Žiarivý výkon (segment->okolie)": f"{Q_rad*1000:.3f} mW",
                       "Max. teplota": f"{T_max:.2f} K",
                       "Poloha max. teploty": f"{x_max_local*1000:.2f} mm",
                       }
            
            # Konfiguruje váhy stĺpcov pre zobrazenie výsledkov
            res_frame.columnconfigure(1, weight=1); res_frame.columnconfigure(3, weight=1)
            result_items = list(results.items())
            num_results = len(result_items)
            split_point = (num_results + 1) // 2
            
            # Zobrazí každý výsledok ako dvojicu popisku (popisok: hodnota)
            for j, (label, value) in enumerate(result_items):
                row, col_offset = (j, 0) if j < split_point else (j - split_point, 2)
                ttk.Label(res_frame, text=f"{label}:").grid(row=row, column=col_offset, sticky="w", padx=5, pady=2)
                ttk.Label(res_frame, text=value, anchor="w", justify=tk.LEFT).grid(row=row, column=col_offset + 1, sticky="ew", padx=(0,10), pady=2)
            cum_L += bar.L # Aktualizuje kumulatívnu dĺžku pre ďalší segment

    def plot_results(self):
        """
        Generuje a zobrazuje Matplotlib graf profilov teploty a tepelného toku
        pozdĺž celej série tyčí. Graf sa otvorí v novom okne Toplevel.
        """
        if not self.series or not self.series.correct:
            messagebox.showwarning("Chýbajú dáta", "Najprv musíte úspešne spustiť analýzu, aby ste mohli vykresliť výsledky.")
            return
        
        # Pretvorí Matplotlib figúru na obrázok
        self.figure.canvas.draw() 
        img_array = np.array(self.figure.canvas.renderer.buffer_rgba()) #
        plt.close(self.figure)        

        # Vytvorí inštanciu triedy GraphWindow, ktorá je sama o sebe oknom Toplevel.
        # Všetka logika pre zobrazenie, zoom a posun je zapuzdrená v tejto triede.
        GraphWindow(self, img_array)

    def save_plot(self):
        """
        Vyzve užívateľa na výber cesty k súboru a uloží vygenerovaný Matplotlib graf
        do obrazového alebo PDF súboru (podporované formáty PNG, PDF, SVG).
        """
        if not self.figure:
            messagebox.showerror("Chýbajú dáta", "Najprv musíte úspešne spustiť analýzu, aby ste mohli vykresliť výsledky.")
            return
        
        # Otvorí dialógové okno na uloženie grafu
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if not filepath:
            return # Užívateľ zrušil dialógové okno
        
        try:
            self.figure.savefig(filepath, dpi=300, bbox_inches='tight') # Uloží figúru
            print(f"[INFO] Graf úspešne uložený do: {filepath}")
        except Exception as e:
            messagebox.showerror("Chyba pri ukladaní", f"Nepodarilo sa uložiť graf: {e}")

    def save_data(self, series, cesta):
        """
        Uloží kompletné výsledkové dáta (pozícia, teplota, vodivosť, tok) do CSV súboru.
        Pridá stĺpec s názvom segmentu pre každú dátovú vzorku.

        Args:
            series (Series): Objekt `Series` s výsledkami.
            cesta (str): Cesta k výstupnému súboru.
        """
        if not series.correct:
            print("[INFO] Ukladanie dát preskočené, pretože analýza nebola úspešná.")
            return
            
        print(f"[INFO] Ukladám výsledné dáta do súboru: {cesta}")
        try:
            # Vytvorenie stĺpca s názvami segmentov pre každý riadok dát
            L_kumul = 0
            nazvy = np.array([], dtype=object)
            for bar in series.bar_list:
                L_kumul += bar.L
                # Nájdenie indexu, kde končí aktuálny segment
                end_idx = np.searchsorted(series.x_plot, L_kumul, side='right')
                # Vytvorenie poľa s opakovaným názvom segmentu
                segment = np.full(end_idx - len(nazvy), bar.nazov, dtype=object)
                nazvy = np.concatenate((nazvy, segment))
            
            # Zabezpečenie, aby dĺžka sedela (pre prípadné zaokrúhľovacie chyby)
            if len(nazvy) < len(series.x_plot):
                nazvy = np.concatenate((nazvy, [series.bar_list[-1].nazov]*(len(series.x_plot)-len(nazvy))))
            nazvy = nazvy[:len(series.x_plot)]
                
            # Zostavenie matice dát pre uloženie
            # .T transponuje maticu, aby stĺpce zodpovedali premenným
            data = np.array([
                nazvy,
                series.x_plot,
                series.T_plot,
                series.k_plot,
                series.Q_plot
            ]).T
            
            header = 'Segment,Pozicia[m],Teplota[K],Vodivost[Wm^{-1}K^{-1}],Tepelny_tok[W]'
            np.savetxt(cesta, data, fmt='%s', delimiter=',', comments='', header=header)
            print(f"[INFO] Dáta úspešne uložené.")
        except Exception as e:
            print(f"[CHYBA] Nepodarilo sa uložiť dáta do súboru. Chyba: {e}")

    def save_data_to_file(self):
        """
        Vyzve užívateľa na výber cesty k súboru a uloží numerické dáta analýzy
        (profily teploty a tepelného toku) do CSV alebo TXT súboru.
        """
        if not self.series or not self.series.correct:
            messagebox.showerror("Chyba", "Nie sú k dispozícii žiadne dáta na uloženie.")
            return
        
        # Otvorí dialógové okno na uloženie dát
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV súbory", "*.csv"), ("TXT súbory", "*.txt")])
        if not filepath:
            return # Užívateľ zrušil dialógové okno
        
        self.save_data(self.series, filepath) # Volá funkciu ukladania dát

    def save_project(self):
        """
        Zozbiera všetky vstupné dáta z GUI a uloží ich do súboru .bsn (JSON formát).
        """
        filepath = filedialog.asksaveasfilename(
            defaultextension=".bsn",
            filetypes=[("BarSerNew Project", "*.bsn"), ("All Files", "*.*")],
            title="Uložiť projekt ako..."
        )
        if not filepath:
            return

        try:
            project_data = {
                'tcd_dir_path': self.tcd_dir_path.get(),
                'globálne okrajové podmienky': {
                    'T0': self.T0_global.get(),
                    'TL': self.TL_global.get()
                },
                'segmenty': [],
                'uzly': []
            }

            # Zozbieranie dát zo segmentov
            for frame in self.bar_frames:
                segment_info = {k: v.get() for k, v in frame.entries.items()}
                project_data['segmenty'].append(segment_info)

            # Zozbieranie dát z uzlov
            for node_frame in self.node_frames:
                node_info = {
                    'ext_q': node_frame.ext_q.get(),
                    'odhad teploty': node_frame.temp_guess.get()
                }
                project_data['uzly'].append(node_info)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=4, ensure_ascii=False)
            
            print(f"[INFO] Projekt úspešne uložený do: {filepath}")
            messagebox.showinfo("Uloženie úspešné", f"Projekt bol uložený do súboru:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Chyba pri ukladaní", f"Nepodarilo sa uložiť projekt: {e}")
            print(f"[CHYBA] Nepodarilo sa uložiť projekt: {e}")

    def load_project(self):
        """
        Načíta projekt zo súboru .bsn a obnoví stav GUI podľa uložených dát.
        """
        filepath = filedialog.askopenfilename(
            filetypes=[("BarSerNew Project", "*.bsn"), ("All Files", "*.*")],
            title="Načítať projekt"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 1. Vyčistiť súčasné GUI
            self._clear_ui_content()
            print(f"\n[INFO] Načítavam projekt zo súboru: {filepath}")

            # 2. Obnoviť globálne nastavenia
            self.tcd_dir_path.set(project_data.get('tcd_dir_path', ''))
            self._update_material_comboboxes()

            global_bc = project_data.get('globálne okrajové podmienky', {})
            self.T0_global.set(global_bc.get('T0', '77.0'))
            self.TL_global.set(global_bc.get('TL', '4.2'))

            # 3. Vytvoriť a naplniť segmenty
            segments_data = project_data.get('segmenty', [])
            if not segments_data:
                self.add_bar_frame() # Ak v projekte nie sú segmenty, pridaj aspoň jeden prázdny
            else:
                for i, seg_data in enumerate(segments_data):
                    self.add_bar_frame()
                    new_frame = self.bar_frames[-1]
                    for key, value in seg_data.items():
                        if key in new_frame.entries:
                            new_frame.entries[key].set(value)
            
            # 4. Naplniť uzly
            nodes_data = project_data.get('uzly', [])
            for i, node_data in enumerate(nodes_data):
                if i < len(self.node_frames):
                    node_frame = self.node_frames[i]
                    node_frame.ext_q.set(node_data.get('ext_q', '0.0'))
                    node_frame.temp_guess.set(node_data.get('odhad teploty', '50.0'))
            
            self._update_segment_labels()
            print("[INFO] Projekt bol úspešne načítaný.")

        except json.JSONDecodeError:
            messagebox.showerror("Chyba pri načítaní", "Súbor má neplatný formát (nie je to platný JSON).")
            print(f"[CHYBA] Súbor '{filepath}' nie je platný JSON súbor.")
        except FileNotFoundError:
            messagebox.showerror("Chyba pri načítaní", "Zadaný súbor nebol nájdený.")
            print(f"[CHYBA] Súbor '{filepath}' nebol nájdený.")
        except Exception as e:
            messagebox.showerror("Chyba pri načítaní", f"Nastala neočakávaná chyba: {e}")
            print(f"[CHYBA] Pri načítavaní projektu nastala chyba: {e}")

    def reset_ui(self):
        """
        Resetuje celé užívateľské rozhranie do počiatočného stavu, vymaže všetky
        vstupné polia, výsledky, konzolové záznamy a deaktivuje relevantné tlačidlá.
        """
        print("\n" + "="*50 + "\n[INFO] Resetujem rozhranie...")
        
        self._clear_ui_content() # <-- ZAVOLÁME NOVÚ METÓDU
        
        # Resetuje vstupné polia globálnych okrajových podmienok na predvolené hodnoty
        self.T0_global.set("77.0")
        self.TL_global.set("4.2")

        # Resetuje cestu k adresáru TCD na predvolenú
        self.tcd_dir_path.set(os.path.join(os.getcwd(), "TCD"))
        self._update_material_comboboxes() # Aktualizujte comboboxy po resetovaní cesty
        
        self.add_bar_frame() # Pridá späť počiatočný predvolený segment
        print("[INFO] Rozhranie bolo resetované.")

    def _clear_ui_content(self):
        """
        Vymaže všetky dynamické vstupné a výstupné prvky GUI.
        Slúži ako základ pre reset alebo načítanie nového projektu.
        """
        # Zničí všetky dynamicky vytvorené rámce segmentov a uzlov
        for frame in self.bar_frames + self.node_frames:
            frame.destroy()
        
        self.bar_frames.clear()  # Vymaže zoznamy obsahujúce referencie na rámce
        self.node_frames.clear()
        
        self.reset_results() # Vymaže obsah panelu výsledkov
        
        # Vyčistí a deaktivuje textovú oblasť konzolového záznamu
        self.log_text.config(state="normal")
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state="disabled")
        
        # Deaktivuje tlačidlá pre graf a uloženie
        self.btn_plot.config(state="disabled")
        self.btn_save_plot.config(state="disabled")
        self.btn_save_data.config(state="disabled")
        
        self.series = None # Vymaže výsledky analýzy
        self.figure = None # Vymaže figúru grafu

    def reset_results(self):
        """
        Vymaže všetky widgety z rolovacieho výstupného rámca, čím efektívne
        odstráni všetky zobrazené výsledky analýzy.
        """
        for widget in self.scrollable_output_frame.winfo_children():
            widget.destroy()

# Vstupný bod aplikácie.
if __name__ == '__main__':
    # Pokúsi sa nastaviť povedomie o DPI pre lepšie škálovanie GUI na Windows s vysokým rozlíšením.
    # Dôležité pre jasné zobrazenie textu a widgetov.
    try:
        # Pre Windows 8.1 a novšie
        windll.shcore.SetProcessDpiAwareness(2)
    except:
        try:
            # Pre Windows 8.0 a staršie
            windll.user32.SetProcessDPIAware()
        except:
            pass
    
    app = ThermalApp() # Vytvorí inštanciu triedy ThermalApp
    app.mainloop()     # Spustí Tkinter slučku udalostí, ktorá riadi interakciu s aplikáciou