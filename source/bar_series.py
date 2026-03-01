import numpy as np
from scipy.optimize import fsolve

class Series:
    """
    Trieda reprezentujúca sériové spojenie viacerých tyčí (Bar objektov).

    Táto trieda riadi proces výpočtu pre sústavu tyčí. Pre jednu tyč len
    spustí jej vlastnú metódu `solve`. Pre viac tyčí používa numerický
    riešič `fsolve` na nájdenie neznámych teplôt na rozhraniach tak,
    aby bola splnená podmienka kontinuity tepelného toku.

    Atribúty:
        bar_list (list): Zoznam `Bar` objektov v sérii.
        ext_Q (np.array): Pole externých tepelných tokov privádzaných
                          na rozhrania medzi tyčami [W].
        correct (bool): Príznak, či sú všetky tyče v sérii korektne inicializované.
        solution_temps (np.array): Pole teplôt na rozhraniach nájdené riešičom.
        x_plot, T_plot, k_plot, Q_plot: Zlúčené polia výsledkov z celej sústavy
                                        pre jednoduché vykresľovanie a analýzu.
    """
    correct = False
    def __init__(self, bar_list, extQ):
        """
        Inicializácia objektu série tyčí.

        Args:
            bar_list (list): Zoznam objektov triedy `Bar`.
            extQ (list): Zoznam externých tepelných tokov [W] privedených na
                         rozhrania. Počet prvkov musí byť o 1 menší ako počet tyčí.
                         Kladná hodnota znamená teplo privedené do rozhrania.
        """
        self.ext_Q = np.array(extQ)
        self.bar_list = bar_list
        # Séria je platná iba vtedy, ak sú všetky jej časti platné
        self.correct = all(bar.correct for bar in bar_list)
        if not self.correct:
            print("[CHYBA] Minimálne jedna z tyčí v sérii nebola správne inicializovaná. Analýza nemôže pokračovať.")

    def solve(self, temp_guess=None):
        """
        Spustí riešenie pre celú sériu tyčí.

        Ak séria obsahuje iba jednu tyč, zavolá jej vlastnú metódu `solve`.
        Ak je tyčí viac, použije `fsolve` na nájdenie teplôt na rozhraniach.

        Args:
            temp_guess (np.array, optional): Počiatočný odhad teplôt na rozhraniach
                                              pre `fsolve`. Ak nie je zadaný, je
                                              potrebné ho poskytnúť.
        """
        if not self.correct:
            print("[INFO] Analýza preskočená kvôli predchádzajúcim chybám.")
            return

        def output():
            """Pomocná vnútorná funkcia na zozbieranie výsledkov z jednotlivých tyčí do jedného celku."""
            x_sum, x, y, T, k, Q = ([], [], [], [], [], [])
            sumL = 0
            for i, bar in enumerate(self.bar_list):
                # Vytvorenie dostatočne hustej siete pre plynulé dáta
                spacing = int(bar.L / 5e-5)
                
                # Zabezpečenie spojitosti x-ovej osi bez duplicitných bodov
                if i != (len(self.bar_list)-1):
                    x_sum.append(np.linspace(sumL, sumL + bar.L, spacing, endpoint=False))
                    x.append(np.linspace(0, bar.L, spacing, endpoint=False))
                else:
                    x_sum.append(np.linspace(sumL, sumL + bar.L, spacing))
                    x.append(np.linspace(0, bar.L, spacing))
                
                sumL += bar.L
                y.append(bar.riesenie.sol(x[i]))
                T.append(y[i][0])       # Teplota T(x)
                k.append(bar.k_func(T[i])) # Vodivosť k(T(x))
                eq = y[i][1]            # Pomocná premenná k(T)*dT/dx
                Q.append(-bar.A * eq)   # Tepelný tok Q(x) = -A * k(T) * dT/dx
            
            # Spojenie dát do jedného poľa pre jednoduché vykresľovanie
            self.x_plot = np.concatenate(x_sum)
            self.T_plot = np.concatenate(T)
            self.k_plot = np.concatenate(k)
            self.Q_plot = np.concatenate(Q)

        # --- Špeciálny prípad: iba jedna tyč ---
        if len(self.bar_list) == 1:
            print('[INFO] Detekovaná jedna tyč. Spúšťam jednoduchú analýzu...')
            bar = self.bar_list[0]
            # Okrajové podmienky sú pevne dané, stačí spustiť riešič pre tyč
            bar.solve()
            if bar.correct:
                self.solution_temps = None # Žiadne vnútorné teploty na riešenie
                print("[INFO] Analýza jednej tyče úspešná.")
                output()
            else:
                self.correct = False
                print("[CHYBA] Analýza jednej tyče zlyhala.")
            return

        # --- Prípad viacerých tyčí v sérii ---
        def Q_residuals(temp):
            """
            Funkcia rezíduí (nevyváženosti) tepelných tokov na rozhraniach.
            
            Táto funkcia je kľúčová pre `fsolve`. Jej cieľom je pre daný odhad
            teplôt na rozhraniach (`temp`) vypočítať "chybu" v bilancii
            tepelných tokov na každom rozhraní. `fsolve` sa snaží nájsť také
            `temp`, pre ktoré táto funkcia vráti vektor núl.

            Args:
                temp (np.array): Pole s odhadovanými teplotami na rozhraniach.
            
            Returns:
                np.array: Pole nevyvážených tokov na jednotlivých rozhraniach.
            """
            int_Q = np.zeros_like(self.ext_Q) # Interné toky na rozhraniach
            try:
                # --- Výpočet tokov pre jednotlivé tyče s aktuálnym odhadom teplôt ---
                # Prvá tyč (pevná T0, premenlivá TL)
                bar0 = self.bar_list[0]
                bar0.TL = temp[0]
                riesenie = bar0.solve()
                # Tepelný tok na konci prvej tyče
                int_Q[0] = -riesenie.sol(bar0.L)[1] * bar0.A

                # Prostredné tyče (premenlivé T0 aj TL)
                for i, bar in enumerate(self.bar_list[1:-1]):
                    bar.T0 = temp[i]
                    bar.TL = temp[i+1]
                    riesenie = bar.solve()
                    # Tok na začiatku tyče prispieva k bilancii ľavého rozhrania
                    int_Q[i] = int_Q[i] + riesenie.sol(0)[1] * bar.A
                    # Tok na konci tyče prispieva k bilancii pravého rozhrania
                    int_Q[i+1] = -riesenie.sol(bar.L)[1] * bar.A

                # Posledná tyč (premenlivá T0, pevná TL)
                barL = self.bar_list[-1]
                barL.T0 = temp[-1]
                riesenie = barL.solve()
                # Tok na začiatku poslednej tyče
                int_Q[-1] = int_Q[-1] + riesenie.sol(0)[1] * barL.A
                
                # Celková bilancia: Súčet interných tokov a externých zdrojov
                # sa musí rovnať nule.
                value = int_Q + self.ext_Q
                
            except Exception as e:
                # Ak výpočet pre nejakú tyč zlyhá (napr. kvôli zlému odhadu `temp`),
                # vrátime veľkú hodnotu, aby `fsolve` vedel, že tento smer je zlý.
                value = np.full_like(temp, 1e6)
            if not all(bar.correct for bar in self.bar_list):
                value = np.full_like(temp, 1e6)
            return value
        
        print('[INFO] Detekovaných viacero tyčí. Spúšťam analýzu série...')
        if temp_guess is None:
            print("[CHYBA] Pre sériu viacerých tyčí je nutné zadať počiatočný odhad teplôt `temp_guess`.")
            self.correct = False
            return
            
        try:
            print("[INFO] Hľadám teploty na rozhraniach pomocou `fsolve`...")
            # `fsolve` hľadá korene funkcie `Q_residuals`
            solution_temps, infodict, ier, mesg = fsolve(Q_residuals, temp_guess, full_output=True)

            if ier != 1:
                print(f"[CHYBA] Riešič `fsolve` nekonvergoval. Správa: {mesg}")
                self.correct = False
                return None
        except Exception as e:
            print(f"[CHYBA] Počas behu `fsolve` nastala neočakávaná chyba: {e}")
            self.correct = False
            return None
        
        residual_sum = np.abs(Q_residuals(solution_temps)).sum()
        if not np.isclose(residual_sum, 0.0, rtol=1e-05, atol=1e-05):
            print(f"[CHYBA] Počas behu `fsolve` nastala neočakávaná chyba, skúste upraviť odhady teplôt na uzloch.")
            self.correct = False
            return None

        
        print("[INFO] Riešič `fsolve` úspešne konvergoval.")
        print(f"       Nájdené teploty na rozhraniach: {solution_temps} K")

        # Finálne spustenie výpočtov s nájdenými teplotami, aby sa uložili správne riešenia
        self.solution_temps = solution_temps
        # Zozbieranie finálnych výsledkov
        output()