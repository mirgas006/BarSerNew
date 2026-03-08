# BarSerNew

**BarSerNew** je simulačný softvér s grafickým používateľským rozhraním (GUI) určený na návrh a rýchle prototypovanie tepelných mostov (thermal links) a chladiacich prstov (cold fingers) v kryogenike.

Tento nástroj umožňuje inžinierom a výskumníkom v počiatočných fázach vývoja realizovať rýchle a spoľahlivé simulácie bez nutnosti vytvárania zložitej CAD geometrie.  

Software je vytvorený ako moderná náhrada za pôvodné programy BarOne1 a BarSer1 vytvorené Ing. Pavlom Hanzelkom na Ústave prístrojovej techniky v Brne.

## Kľúčové vlastnosti
* **Jednoduché GUI:** Na rozdiel od svojich MS-DOS predchodcov (BarOne1 a BarSer1), BarSerNew ponúka moderné rozhranie, ktoré zjednodušuje prácu.
* **Rýchlosť a efektivita:** Redukovaný výpočtový čas v porovnaní s predchádzajúcimi verziami.
* **Komplexné okrajové podmienky:** Možnosť definovať teploty na koncoch systému, vnútorné a vonkajšie tepelné toky a teplotu okolitého prostredia (pre výpočet tepelného žiarenia).
* **Vstavané nástroje:** Integrovaná kalkulačka geometrie, detailný export dát a zabudované vykresľovanie (plotting) grafov.

## Ako to funguje
Softvér rieši ustálený jednorozmerný okrajový problém toku tepla (steady-state 1D heat-flow boundary problem). Systém modeluje ako reťazec jednorozmerných tyčových prvkov (bar elements) zapojených do série. 

## Reálne využitie a validácia
Softvér bol úspešne použitý na návrh a optimalizáciu medeného chladiaceho prsta pre LN₂ Dewarovu nádobu, ktorá slúži na konverziu štandardného SEM na Cryo-SEM. 
Simulované teploty na špičke chladiaceho prsta vykázali **výbornú zhodu s experimentálnymi meraniami** na plne funkčnom prototype, čo potvrdzuje spoľahlivosť softvéru pri reálnom dizajne kryogénnych systémov.

## Inštalácia a spustenie
Štruktúra zložky:  
	--> dist - zložka vytvorená kompilátorom, obsahuje skompilovaný program BarSerNew.exe pre uživateľa  
	--> source - zložka obsahujúca zdrojový kód  
	--> build - zložka vytvorená kompilátorom  
	--> BarSerNew.spec - súbor vytvorený kompilátorom  

Uživateľ nepotrebuje celú túto zložku, pre funkčnosť programu postačuje obsah zložky dist.  
Nové materiálové súbory stačí umiestniť do zložky dist/TCD.

Použitý software (Python a jeho knižnice):  
	python==3.12.6  
	scipy==1.14.1  
	numpy==2.1.1  
	pillow==11.0.0  
	matplotlib==3.9.2  
	pywin32-ctypes==0.2.3  
	pyinstaller==6.14.1  


Pre skompilovanie v CMD v tejto zložke spustiť:  
pyinstaller --windowed --onefile --name "BarSerNew" --icon "source/ikonka.ico" --add-binary "source/ikonka.png;." source/gui.py


