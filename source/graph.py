import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt

def plot(series):
    """
    Vykreslí výsledky analýzy do troch pod-sebových grafov.

    Generuje grafy pre teplotný profil T(x), priebeh tepelného toku Q(x)
    a priebeh tepelnej vodivosti k(x). V prípade viacerých segmentov
    pridáva zvislé čiary na označenie rozhraní.

    Args:
        series (Series): Objekt `Series` obsahujúci výsledky analýzy.
    """
    if not series.correct:
        print("[INFO] Vykresľovanie grafov preskočené, pretože analýza nebola úspešná.")
        return
    
    print("[INFO] Generujem grafy výsledkov...")

    # --- PRÍPRAVA DÁT PRE GRAFY ---
    # Dáta sa berú priamo z `series` objektu, kde boli pripravené metódou `output`.
    x_plot = series.x_plot
    T_plot = series.T_plot
    k_plot = series.k_plot
    Q_plot = series.Q_plot

    # --- DEFINÍCIA VEĽKOSTI FONTOV PRE GRAFY ---
    TITLE_FONTSIZE = 16
    LABEL_FONTSIZE = 14
    LEGEND_FONTSIZE = 12
    TICK_FONTSIZE = 12

    # --- VYTVORENIE GRAFOV ---
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 21))

    # --- 1. GRAF: Teplotný profil T(x) ---
    ax1.set_ylabel(r'Teplota, $T\ [K]$', fontsize=LABEL_FONTSIZE)
    ax1.plot(x_plot * 1000, T_plot, color='tab:red', linewidth=2, label=r'Teplota $T\ (x)$')
    ax1.set_title('Teplotný profil', fontsize=TITLE_FONTSIZE)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.tick_params(axis='y', labelsize=TICK_FONTSIZE)

    # --- 2. GRAF: Tepelný tok Q(x) ---
    ax2.set_ylabel(r'Tepelný tok, $Q\ [mW]$', fontsize=LABEL_FONTSIZE)
    ax2.plot(x_plot * 1000, Q_plot * 1000, color='tab:green', linewidth=2, label=r'Tepelný tok $Q\ (x)$')
    ax2.set_title('Priebeh tepelného toku', fontsize=TITLE_FONTSIZE)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.tick_params(axis='y', labelsize=TICK_FONTSIZE)

    # --- 3. GRAF: Tepelná vodivosť k(T(x)) ---
    ax3.set_ylabel(r'Vodivosť, $\lambda\ [W m^{-1} K^{-1}]$', fontsize=LABEL_FONTSIZE)
    ax3.plot(x_plot * 1000, k_plot, color='tab:blue', linewidth=2, label=r'Vodivosť $\lambda\ (x)$')
    ax3.set_title('Priebeh tepelnej vodivosti', fontsize=TITLE_FONTSIZE)
    ax3.grid(True, linestyle=':', alpha=0.6)
    ax3.tick_params(axis='y', labelsize=TICK_FONTSIZE)
    
    # Popis osi x
    ax1.set_xlabel(r'Pozícia na tyči, $x\ [mm]$', fontsize=LABEL_FONTSIZE)
    ax1.tick_params(axis='x', labelsize=TICK_FONTSIZE)
    ax2.set_xlabel(r'Pozícia na tyči, $x\ [mm]$', fontsize=LABEL_FONTSIZE)
    ax2.tick_params(axis='x', labelsize=TICK_FONTSIZE)
    ax3.set_xlabel(r'Pozícia na tyči, $x\ [mm]$', fontsize=LABEL_FONTSIZE)
    ax3.tick_params(axis='x', labelsize=TICK_FONTSIZE)

    # zabránenie "skritia" výsledku do koeficientu
    ax1.ticklabel_format(useOffset=False)
    ax2.ticklabel_format(useOffset=False)
    ax3.ticklabel_format(useOffset=False)

    # --- PRIDANIE VERTIKÁLNYCH ČIAR PRE ODDELENIE SEGMENTOV ---
    if len(series.bar_list) > 1:
        interface_position = 0
        for bar in series.bar_list[:-1]:
            interface_position += bar.L
            interface_position_mm = interface_position * 1000
            line_style = {'color': 'gray', 'linestyle': '--', 'linewidth': 1.5}
            ax1.axvline(x=interface_position_mm, **line_style)
            ax2.axvline(x=interface_position_mm, **line_style)
            ax3.axvline(x=interface_position_mm, **line_style)
        
        # Pridanie popisu pre čiaru do legendy
        ax1.plot([], [], **line_style, label='Rozhrania')
        ax2.plot([], [], **line_style, label='Rozhrania')
        ax3.plot([], [], **line_style, label='Rozhrania')

    for ax in [ax1, ax2, ax3]:
        ax.legend(fontsize=LEGEND_FONTSIZE)

    plt.tight_layout(pad=1.5, rect=[0, 0, 1, 0.97])
    #plt.show()
    return fig

class GraphWindow(tk.Toplevel):
    """
    Trieda reprezentujúca okno na zobrazenie grafu s interaktívnymi funkciami.

    Každá inštancia tejto triedy je samostatné okno, ktoré zobrazí obrázok
    poskytnutý ako NumPy pole. Implementuje funkcie pre priblíženie (zoom)
    pomocou kolieska myši alebo kliknutím a posúvanie (pan) obrázka ťahaním
    myšou. Okno je modálne a zostáva nad hlavnou aplikáciou.

    Atribúty:
        original_pil_image (PIL.Image): Pôvodný obrázok, ktorý sa nemení.
        current_pil_image (PIL.Image): Aktuálna verzia obrázka po zmene veľkosti.
        tk_image (ImageTk.PhotoImage): Obrázok vo formáte pre Tkinter.
        image_label (tk.Canvas): Widget, na ktorom je obrázok vykreslený.
        image_on_canvas (int): ID obrázka na plátne (Canvas).
        zoom_factor_current (float): Aktuálny faktor priblíženia.
        start_x, start_y (int): Súradnice pre začiatok posúvania.
        start_x0, start_y0 (int): Súradnice pre rozlíšenie kliku od ťahania.
    """
    def __init__(self, master, img_array):
        """
        Inicializácia okna s grafom.

        Args:
            master: Rodičovské okno (hlavná aplikácia).
            img_array (np.array): Vstupné NumPy pole reprezentujúce obrázok.
        """
        super().__init__(master)
        self.title("Graf (Ľavý klik: priblíženie, Pravý klik: oddialenie, Ťahanie: posun)")
        self.attributes('-topmost', True)  # Okno bude vždy nad hlavným oknom
        
        # Konverzia NumPy poľa na PIL Image objekt.
        self.original_pil_image = Image.fromarray(img_array)
        self.current_pil_image = self.original_pil_image.copy()
        self.tk_image = None

        # Premenné pre stav interakcie
        self.zoom_factor_current = 0.6
        self.start_x = self.start_y = None
        self.start_x0 = self.start_y0 = None

        self._create_widgets()
        self._bind_events()
        self._update_image()

    def _create_widgets(self):
        """
        Vytvorí a usporiada widgety v okne, primárne Canvas pre obrázok.
        """
        # Konverzia PIL Image na Tkinter PhotoImage pre prvé zobrazenie.
        self.tk_image = ImageTk.PhotoImage(self.original_pil_image)

        # Vytvorenie Canvas widgetu, ktorý slúži ako plocha pre obrázok.
        self.image_label = tk.Canvas(self, height=self.tk_image.height(), width=self.tk_image.width(), bg="white", cursor='diamond_cross')
        
        # Uchovanie referencie na tk_image, aby ju Python "garbage collector" nezmazal.
        self.image_label.tk_image = self.tk_image
        
        # Vytvorenie obrázka na Canvas, umiestneného v ľavom hornom rohu.
        self.image_on_canvas = self.image_label.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
        
        # Zbalenie Canvas widgetu do okna.
        self.image_label.pack(padx=10, pady=10, fill="both", expand=True)

    def _bind_events(self):
        """
        Naviaže udalosti myši (klik, ťahanie, koliesko) na príslušné metódy.
        """
        # Naviazanie udalostí kolieska myši pre zoom.
        self.image_label.bind('<MouseWheel>', self._do_zoom)    # Windows/Mac
        self.image_label.bind('<Button-4>', self._do_zoom)      # Linux (koliesko hore)
        self.image_label.bind('<Button-5>', self._do_zoom)      # Linux (koliesko dole)
        
        # Naviazanie udalostí pre ťahanie (ľavé aj pravé tlačidlo).
        self.image_label.bind('<Button-1>', self._start_drag)
        self.image_label.bind('<B1-Motion>', self._do_drag)
        self.image_label.bind('<Button-3>', self._start_drag)
        self.image_label.bind('<B3-Motion>', self._do_drag)

        # Naviazanie uvoľnenia tlačidiel pre rozlíšenie klik vs. ťahanie.
        self.image_label.bind('<ButtonRelease-1>', self._handle_button1_release)
        self.image_label.bind('<ButtonRelease-3>', self._handle_button3_release)
        
    def _update_image(self):
        """
        Aktualizuje zobrazenie obrázka na Canvas po priblížení/oddialení.

        Prepočíta nové rozmery obrázka, zmení veľkosť PIL Image a následne
        aktualizuje Tkinter PhotoImage na Canvas widgete.
        """
        # Výpočet nových rozmerov na základe pôvodných rozmerov a zoom faktora.
        width, height = self.original_pil_image.size
        new_width = int(width * self.zoom_factor_current)
        new_height = int(height * self.zoom_factor_current)

        # Zmena veľkosti PIL obrázka s použitím LANCZOS filtra pre vyhladenie.
        self.current_pil_image = self.original_pil_image.resize((new_width, new_height), Image.LANCZOS)
        
        # Vytvorenie nového Tkinter PhotoImage z upraveného PIL Image.
        self.tk_image = ImageTk.PhotoImage(self.current_pil_image)
        
        # Aktualizácia obrázka na Canvas.
        self.image_label.itemconfig(self.image_on_canvas, image=self.tk_image)
        
        # Aktualizácia rozmerov Canvas, aby zodpovedal novým rozmerom obrázka.
        self.image_label.config(width=new_width, height=new_height)

    def _do_zoom(self, event):
        """
        Vykonáva priblíženie alebo oddialenie na základe udalosti kolieska myši.

        Args:
            event (tk.Event): Objekt udalosti myši.
        """
        zoom_step = 1.1
        # `event.delta` pre Windows/Mac, `event.num` pre Linux.
        if event.delta > 0 or event.num == 4:  # Koliesko hore -> zoom in
            self.zoom_factor_current *= zoom_step
        elif event.delta < 0 or event.num == 5:  # Koliesko dole -> zoom out
            self.zoom_factor_current /= zoom_step
        
        # Obmedzenie priblíženia, aby sa zabránilo príliš malému/veľkému obrázku.
        self.zoom_factor_current = max(0.25, min(self.zoom_factor_current, 2.5))
        self._update_image()

    def _zoom_in(self):
        """Vykoná jeden krok priblíženia (zoom in)."""
        self.zoom_factor_current *= 1.2
        self.zoom_factor_current = min(self.zoom_factor_current, 2.5)
        self._update_image()

    def _zoom_out(self):
        """Vykoná jeden krok oddialenia (zoom out)."""
        self.zoom_factor_current /= 1.2
        self.zoom_factor_current = max(0.25, self.zoom_factor_current)
        self._update_image()

    def _start_drag(self, event):
        """
        Inicializuje proces presúvania zaznamenaním počiatočných súradníc.
        
        Args:
            event (tk.Event): Objekt udalosti myši.
        """
        # Uloženie počiatočných súradníc myši na Canvas.
        self.start_x = self.image_label.canvasx(event.x)
        self.start_y = self.image_label.canvasy(event.y)
        self.start_x0 = self.image_label.canvasx(event.x)
        self.start_y0 = self.image_label.canvasy(event.y)

    def _do_drag(self, event):
        """
        Vykonáva presúvanie obrázka počas ťahania myšou.

        Args:
            event (tk.Event): Objekt udalosti myši.
        """
        if self.start_x is not None and self.start_y is not None:
            cur_x = self.image_label.canvasx(event.x)
            cur_y = self.image_label.canvasy(event.y)
            
            # Výpočet zmeny pozície (delta x, delta y).
            dx = cur_x - self.start_x
            dy = cur_y - self.start_y
            
            # Posunutie obrázka na Canvas.
            self.image_label.move(self.image_on_canvas, dx, dy)
            
            # Aktualizácia počiatočných súradníc pre ďalší krok.
            self.start_x = cur_x
            self.start_y = cur_y

    def _handle_button1_release(self, event):
        """
        Spracuje uvoľnenie ľavého tlačidla myši. Ak nedošlo k ťahaniu,
        vykoná priblíženie. Inak ukončí režim ťahania.
        """
        cur_x = self.image_label.canvasx(event.x)
        cur_y = self.image_label.canvasy(event.y)
        # Ak bol pohyb myši minimálny, považuje sa to za klik.
        if (abs(self.start_x0 - cur_x) < 2) and (abs(self.start_y0 - cur_y) < 2):
            self._zoom_in()
        
        # Reset stavu pre ťahanie.
        self.start_x = self.start_y = None
        self.start_x0 = self.start_y0 = None

    def _handle_button3_release(self, event):
        """
        Spracuje uvoľnenie pravého tlačidla myši. Ak nedošlo k ťahaniu,
        vykoná oddialenie. Inak ukončí režim ťahania.
        """
        cur_x = self.image_label.canvasx(event.x)
        cur_y = self.image_label.canvasy(event.y)
        # Ak bol pohyb myši minimálny, považuje sa to za klik.
        if (abs(self.start_x0 - cur_x) < 2) and (abs(self.start_y0 - cur_y) < 2):
            self._zoom_out()

        # Reset stavu pre ťahanie.
        self.start_x = self.start_y = None
        self.start_x0 = self.start_y0 = None