# AdminAI

AdminAI je jednoduchý asistenční program s grafickým rozhraním pro správu administrativních úkolů, jako je plánování schůzek, správa e-mailů, vyplňování formulářů, archivace dokumentů, plánování úkolů a generování reportů.

## Funkce

- **Plánování schůzek** – možnost uložit schůzky s datem, časem a účastníky.
- **Správa e-mailů** – třídění e-mailů podle odesílatele a přesun do složek.
- **Vyplňování formulářů** – automatické vyplňování údajů a uložení do souboru.
- **Archivace dokumentů** – přesunutí souborů do archivační složky.
- **Plánování úkolů** – přidávání úkolů s termíny.
- **Generování reportů** – vytvoření textového přehledu schůzek.

## Požadavky

- Python 3.x
- Knihovny: `sqlite3`, `tkinter`, `os`, `datetime`

## Instalace a spuštění

1. Stáhněte nebo naklonujte tento repozitář.
2. Ujistěte se, že máte nainstalovaný Python 3.
3. Spusťte skript pomocí příkazu:
   ```bash
   python AdminAI.py
   ```

## Použití

Po spuštění programu se zobrazí hlavní okno s menu. Lze zadávat příkazy do textového pole nebo využít menu pro jednotlivé funkce.

Příklady příkazů:
- `naplánuj schůzku v 10:00 s týmem`
- `roztřiď e-maily od šéf do důležité`
- `vyplň formulář`
- `archivuj dokument do smluvy`
- `přidej úkol: Odeslat fakturu do pátku`
- `vytvoř přehled schůzek`

## Databáze

Program využívá databázi `adminai.db`, kde ukládá informace o schůzkách, e-mailech, úkolech a uživatelských preferencích.

## Autor
Lukáš Drštička, Mindlore AI Solutions


