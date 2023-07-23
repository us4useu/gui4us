
from gui4us.model.envs.arrus import UltrasoundEnv

# Zaladowanie tego pliku spowoduje otworzenie sesji
# Nastepnie uzytkownik edytuje w tym pliku ustawienia
# Nastepnie naciska reset environment
# w jaki sposob reset w tym srodowisku powinno odczytac jeszcze raz ustawienia
# byc moze zamiast reset state, to akcja: zmien parametry sesji
#

# Generalnie plik ze schematem powinien byc mozliwy do edycji w dowolnym momencie
# Plik z schematem moze byc plikiem pythonowym
# plik pytohnowy moze byc edytowany przez uzytkownika, nastepnie srodowisko moze zostac zresetowane programowo
#

ENV = UltrasoundEnv(
    settings="us4r.prototxt",
    # Zamiast tego parametru: plik srodowiska powinien byc modulem/pakietem pythonowym
    scheme="scheme.py",

)

ENV.set_scheme_file("")
# UWAGA: to moze zmienic wymiary obrazka! konieczny jest reset calego srodowiska
# Na razie prosciej: zaimplementowac zmiane przez reset srodowiska.
# Reset:
# zwraca nowe metadane
# triggeruje reset widoku (usuwany jest stary widok, wlaczany jest nowy)
# W przyszlosci:
# istotne jest to, ze niektore z akcji moga skutkowac zmiana
# Ponizej jest async environment.
# W async environment obserwacje nie sa wylacznie reakcja na przychodzace dane

# Env.act powinno zwracac informacje, czy zmienily sie metadane, i zwracac odpowiednio nowe metadane
# informacje o
# EnvSync.act tez nie powinien zwracac danych
#
