Štruktúra zložky:
	--> dist - zložka vytvorená kompilátorom, obsahuje skompilovaný program pre uživateľa
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