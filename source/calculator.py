import tkinter as tk
from tkinter import ttk, messagebox
import math

class GeometryCalculatorWindow(tk.Toplevel):
    """
    Okno kalkulačky pre výpočet prierezu a obvodu geometrických tvarov.
    Umožňuje používateľovi vybrať si medzi obdĺžnikom a kruhom, zadať rozmery
    a po potvrdení automaticky vyplní príslušné polia v hlavnom GUI.
    """
    def __init__(self, master, entries_to_update):
        """
        Inicializácia okna kalkulačky.

        Args:
            master: Rodičovské okno (hlavná aplikácia).
            entries_to_update (dict): Slovník s Tkinter premennými (StringVar),
                                      ktoré sa majú aktualizovať po výpočte.
                                      Očakáva kľúče "Prierez [mm^2]" a "Obvod [mm]".
        """
        super().__init__(master)
        self.title("Kalkulačka prierezu")
        self.transient(master) # Okno bude vždy nad hlavným oknom
        self.grab_set() # Zablokuje interakciu s hlavným oknom
        self.resizable(False, False)

        self.entries_to_update = entries_to_update
        self.shape_var = tk.StringVar(value="obdlznik")

        self._create_widgets()
        self._on_shape_change() # Nastaví počiatočnú viditeľnosť

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill="both", expand=True) # main_frame itself is still packed into the Toplevel window

        # Configure columns for main_frame if using grid for its children
        main_frame.columnconfigure(0, weight=1) # This makes the content expand horizontally

        # --- Výber tvaru ---
        shape_frame = ttk.LabelFrame(main_frame, text=" Tvar prierezu ", padding=10)
        shape_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10)) # Changed to grid
        
        ttk.Radiobutton(shape_frame, text="Obdĺžnik", variable=self.shape_var, value="obdlznik", command=self._on_shape_change).pack(side="left", padx=10)
        ttk.Radiobutton(shape_frame, text="Kruh", variable=self.shape_var, value="kruh", command=self._on_shape_change).pack(side="left", padx=10)

        # --- Rámec pre rozmery obdĺžnika ---
        self.rect_frame = ttk.LabelFrame(main_frame, text=" Rozmery obdĺžnika ", padding=10)
        self.rect_frame.grid(row=1, column=0, sticky="ew", pady=5) # Changed row to 1
        self.rect_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.rect_frame, text="Šírka [mm]:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.rect_width = tk.StringVar()
        ttk.Entry(self.rect_frame, textvariable=self.rect_width).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(self.rect_frame, text="Výška [mm]:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.rect_height = tk.StringVar()
        ttk.Entry(self.rect_frame, textvariable=self.rect_height).grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        # --- Rámec pre rozmery kruhu ---
        self.circle_frame = ttk.LabelFrame(main_frame, text=" Rozmery kruhu ", padding=10)
        self.circle_frame.grid(row=1, column=0, sticky="ew", pady=5) # Changed row to 1
        self.circle_frame.columnconfigure(1, weight=1)

        ttk.Label(self.circle_frame, text="Priemer [mm]:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.circle_diameter = tk.StringVar()
        ttk.Entry(self.circle_frame, textvariable=self.circle_diameter).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        # --- Tlačidlá ---
        button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        button_frame.grid(row=2, column=0, sticky="ew") # Changed row to 2
        
        ttk.Button(button_frame, text="Vypočítať a použiť", style="Accent.TButton", command=self._calculate_and_apply).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(button_frame, text="Zrušiť", command=self.destroy).pack(side="left", expand=True, fill="x", padx=(5, 0))

    def _on_shape_change(self):
        """Skryje/zobrazí rámce podľa zvoleného tvaru."""
        if self.shape_var.get() == "obdlznik":
            self.rect_frame.grid() # Zobrazí rámec obdĺžnika
            self.circle_frame.grid_remove() # Skryje rámec kruhu
        else: # kruh
            self.rect_frame.grid_remove() # Skryje rámec obdĺžnika
            self.circle_frame.grid() # Zobrazí rámec kruhu
            
    def _calculate_and_apply(self):
        """Vypočíta plochu a obvod a aktualizuje hlavné GUI."""
        try:
            if self.shape_var.get() == "obdlznik":
                w = float(self.rect_width.get().replace(',', '.'))
                h = float(self.rect_height.get().replace(',', '.'))
                if w <= 0 or h <= 0: raise ValueError("Rozmery musia byť kladné.")
                
                area = w * h
                perimeter = 2 * (w + h)
            else: # kruh
                d = float(self.circle_diameter.get().replace(',', '.'))
                if d <= 0: raise ValueError("Priemer musí byť kladný.")

                radius = d / 2
                area = math.pi * (radius ** 2)
                perimeter = math.pi * d
            
            # Aktualizácia StringVars v hlavnom okne
            self.entries_to_update["Prierez [mm^2]"].set(f"{area:.4f}")
            self.entries_to_update["Obvod [mm]"].set(f"{perimeter:.4f}")
            
            self.destroy() # Zatvorenie okna kalkulačky

        except ValueError as e:
            messagebox.showerror("Chybný vstup", f"Zadajte platné kladné čísla.\nChyba: {e}", parent=self)
        except Exception as e:
            messagebox.showerror("Chyba", f"Nastala neočakávaná chyba: {e}", parent=self)