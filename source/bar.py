import numpy as np
from scipy.interpolate import interp1d
from scipy.integrate import solve_bvp
from scipy.constants import sigma

class Bar:
    """
    Trieda reprezentujúca jednu tyč (segment) pre analýzu vedenia tepla.

    Každá inštancia tejto triedy obsahuje všetky fyzikálne a materiálové
    parametre potrebné na definovanie a riešenie 1D stacionárnej rovnice
    vedenia tepla s teplotne závislou tepelnou vodivosťou a tepelnými
    stratami žiarením.

    Atribúty:
        nazov (str): Názov alebo identifikátor tyče.
        L (float): Dĺžka tyče [m].
        A (float): Plocha prierezu [m^2].
        P (float): Obvod prierezu [m].
        epsilon (float): Emisivita povrchu tyče.
        T_okolie (float): Teplota okolia [K].
        T0 (float): Okrajová podmienka teploty na začiatku tyče (x=0) [K].
        TL (float): Okrajová podmienka teploty na konci tyče (x=L) [K].
        subor (str): Cesta k .TCD súboru s dátami o tepelnej vodivosti.
        correct (bool): Príznak, či bola inicializácia a načítanie dát úspešné.
        k_func (interp1d): Interpolačná funkcia pre tepelnú vodivosť k(T).
        min_T (float): Minimálna teplota z tabuľky vodivostí [K].
        max_T (float): Maximálna teplota z tabuľky vodivostí [K].
        riesenie (OdeResult): Objekt obsahujúci výsledok z numerického riešiča.
    """
    correct = False

    def __init__(self, nazov, subor, L, A, P, epsilon, T0, TL, T_okolie):
        """
        Inicializácia objektu tyče.

        Args:
            nazov (str): Názov tyče (napr. 'Hlinikova tyc').
            subor (str): Cesta k súboru s tabuľkovými dátami vodivosti.
            L (float): Dĺžka tyče [m].
            A (float): Plocha prierezu [m^2].
            P (float): Obvod prierezu [m] (pre výpočet strát žiarením).
            epsilon (float): Emisivita povrchu (hodnota medzi 0 a 1).
            T0 (float): Teplota na ľavom konci (x=0) [K].
            TL (float): Teplota na pravom konci (x=L) [K].
            T_okolie (float): Teplota okolitého prostredia [K].
        """
        self.nazov = nazov
        self.L = L
        self.A = A
        self.P = P
        self.epsilon = epsilon
        self.T_okolie = T_okolie
        self.T0 = T0
        self.TL = TL
        self.subor = subor
        
        self.nacitaj_interpoluj()

    def nacitaj_interpoluj(self):
        """
        Načíta dáta o tepelnej vodivosti zo súboru a vytvorí interpolačnú funkciu.

        Metóda sa pokúsi otvoriť zadaný súbor, preskočiť úvodné textové riadky
        a načítať tabuľku s dvoma stĺpcami (Teplota, Vodivosť). Z týchto dát
        vytvorí lineárnu interpolačnú funkciu k(T), ktorú uloží do `self.k_func`.
        """
        data_rows = []
        try:
            with open(self.subor, 'r') as f:
                for line in f:
                    # Rozdelí riadok podľa akýchkoľvek bielych znakov (medzery, tabulátory)
                    parts = line.split()
                    # Preskočí riadky, ktoré nemajú aspoň 2 stĺpce
                    if len(parts) < 2:
                        continue
                    
                    try:
                        # Pokúsi sa prekonvertovať prvé dva stĺpce na čísla
                        teplota = float(parts[0])
                        vodivost = float(parts[1])
                        # Ak sa to podarí, pridá dáta do zoznamu
                        data_rows.append([teplota, vodivost])
                    except (ValueError, IndexError):
                        # Ak konverzia zlyhá, ide pravdepodobne o hlavičku, tak ju ignorujeme
                        continue
            
            if not data_rows:
                raise ValueError(f"[CHYBA] V súbore '{self.nazov}' sa nenašli žiadne platné dátové riadky.")

            # Prevedie zoznam dát na NumPy pole
            data = np.array(data_rows)
            teploty = data[:, 0]
            vodivosti = data[:, 1]
            
            # Uloženie minimálnej a maximálnej teploty pre kontrolu extrapolácie
            self.min_T = teploty.min()
            self.max_T = teploty.max()
            
            # Vytvorenie lineárnej interpolačnej funkcie.
            self.k_func = interp1d(teploty, vodivosti, kind='linear')
            
            print(f"[INFO] Dáta o vodivosti pre '{self.nazov}' úspešne načítané.")
            print(f"       Definovaný teplotný rozsah: [{self.min_T:.2f} K, {self.max_T:.2f} K].")
            self.correct = True

        except FileNotFoundError:
            print(f"[CHYBA] Súbor '{self.subor}' nebol nájdený. Objekt '{self.nazov}' je neplatný.")
            self.correct = False
        except Exception as e:
            print(f"[CHYBA] Nepodarilo sa spracovať súbor '{self.subor}'. Skontrolujte formát. Chyba: {e}")
            self.correct = False
        
    def solve(self):
        """
        Spustí numerické riešenie rovnice vedenia tepla pre danú tyč.

        Táto metóda obaľuje vnútornú funkciu `solver`, ktorá vykonáva všetky
        kroky potrebné na riešenie okrajovej úlohy pomocou `scipy.integrate.solve_bvp`.
        Výsledok ukladá do `self.riesenie`.
        """
        # Vnútorná funkcia, aby sa predišlo opakovanému posielaniu 'self'
        def solver(bar):
            def definuj_system_rovnic(x, y):
                """
                Definuje systém diferenciálnych rovníc 1. rádu pre riešič.
                
                Pôvodná rovnica 2. rádu: d(k(T) * dT/dx)/dx = (P*epsilon*sigma/A) * (T⁴ - T_okolie⁴)
                
                Prevod na systém 1. rádu zavedením substitúcie:
                y[0] = T(x)          (teplota)
                y[1] = k(T) * dT/dx  (pomocná premenná reprezentujúca tok tepla bez plochy)
                
                Diferenciálne rovnice systému:
                dy[0]/dx = dT/dx = y[1] / k(T(x))
                dy[1]/dx = d(k(T)*(dT/dx))/dx = C * (T⁴ - T_okolie⁴), kde C je konštanta
                """
                T = y[0]
                k_dT_dx = y[1]
                
                # Bezpečnostná kontrola, aby riešič neextrapoloval mimo rozsahu dát
                if np.any(T < bar.min_T) or np.any(T > bar.max_T):
                    mimo_rozsahu = T[(T < bar.min_T) | (T > bar.max_T)][0]
                    raise ValueError(
                        f"[CHYBA] POKUS O EXTRAPOLÁCIU PRI VÝPOČTE '{bar.nazov}'!\n"
                        f"        Požadovaná teplota {mimo_rozsahu:.2f} K je mimo platného rozsahu  dát [{bar.min_T:.2f} K, {bar.max_T:.2f} K]\n"
                        f"        definovaného v '{bar.subor}'."
                    )
                
                # Získanie hodnoty vodivosti pre danú teplotu T
                k_val = bar.k_func(T)
                
                # Prvá rovnica systému

                # Ak je vodivosť numericky nulová, nahradíme ju veľmi malým číslom,
                # aby sa predišlo chybe a umožnilo riešiču pokračovať.
                if np.any(np.isclose(k_val, 0, atol=1e-12, rtol=1e-12)):
                    k_val[np.isclose(k_val, 0)] = 1e-12
                dT_dx = k_dT_dx / k_val
                
                # Konštanta pre druhú rovnicu
                C = (bar.epsilon * sigma * bar.P) / bar.A
                # Druhá rovnica systému (člen reprezentujúci straty žiarením)
                d_k_dT_dx_dx = C * (T**4 - bar.T_okolie**4)
                
                # Vrátenie poľa derivácií [dy[0]/dx, dy[1]/dx]
                return np.vstack((dT_dx, d_k_dT_dx_dx))

            def definuj_okrajove_podmienky(ya, yb):
                """
                Definuje okrajové podmienky pre riešič.
                Riešič `solve_bvp` vyžaduje, aby funkcia vracala nuly, keď sú
                okrajové podmienky splnené.

                ya: hodnoty riešenia na ľavom konci (x=0), ya[0] = T(0)
                yb: hodnoty riešenia na pravom konci (x=L), yb[0] = T(L)

                Podmienky:
                T(0) = T0  =>  ya[0] - bar.T0 = 0
                T(L) = TL  =>  yb[0] - bar.TL = 0
                """
                return np.array([ya[0] - bar.T0, yb[0] - bar.TL])

            # KROK 1: VYTVORENIE SIETE PRE RIEŠENIE
            # Riešič potrebuje počiatočnú sieť bodov, v ktorých bude hľadať riešenie.
            # Hustota siete (napr. bod každé 2 mm) ovplyvňuje stabilitu riešenia.
            spacing = max(10, round(bar.L / 0.002)) # aspon 10 bodov
            x_siet = np.linspace(0, bar.L, spacing)

            # KROK 2: POČIATOČNÝ ODHAD RIEŠENIA
            # Pre nelineárne problémy je nutné poskytnúť počiatočný odhad riešenia.
            # Lineárny profil od T0 po TL je zvyčajne dostatočne dobrý prvý odhad.
            T_odhad = np.linspace(bar.T0, bar.TL, len(x_siet))
            # Odhad pre y[1] môže byť nula, riešič si ho prispôsobí.
            y_odhad = np.vstack((T_odhad, np.zeros_like(x_siet)))

            # KROK 3: SPUSTENIE NUMERICKÉHO RIEŠIČA
            # `solve_bvp` hľadá riešenie okrajovej úlohy.
            riesenie = solve_bvp(definuj_system_rovnic, definuj_okrajove_podmienky, x_siet, y_odhad, max_nodes=10000)
            return riesenie
        
        try:
            # Volanie vnútornej funkcie solver
            riesenie = solver(self)
            self.riesenie = riesenie
            # Kontrola úspešnosti výpočtu
            if not riesenie.success:
                print(f"[VAROVANIE] Výpočet pre '{self.nazov}' nebol úspešný!")
                print(f"           Správa od riešiča: {riesenie.message}")
                self.correct = False
            else:
                self.correct = True

        except ValueError as e:
            # Zachytenie chyby extrapolácie z `definuj_system_rovnic`
            print(f"{e}")
            self.correct = False
            raise Exception
        return riesenie