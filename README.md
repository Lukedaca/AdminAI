# AdminAI - Personální Asistent s AI

## 📝 Popis projektu

AdminAI je chytrý **personální asistent**, který pomáhá **automatizovat administrativní úkony** a **generovat obsah** pomocí **AI modelu DistilGPT-2**. Aplikace umožňuje snadnou správu schůzek, úkolů, e-mailů a dokumentů, přičemž využívá **strojové učení** pro zlepšení uživatelského zážitku.

## 🎯 Klíčové funkce

✅ **Správa schůzek** – plánování a zobrazení seznamu schůzek ✅ **Správa úkolů** – přidávání, editace a dokončení úkolů ✅ **E-mailový asistent** – generování a odesílání e-mailů ✅ **Generátor obsahu** – tvorba textů pro web, Facebook a reporty ✅ **Připomenutí** – upozornění na důležité události ✅ **Analýza a statistiky** – vizualizace schůzek a úkolů ✅ **Uživatelské preference** – přizpůsobení podle zvyklostí uživatele ✅ **Lokální AI (DistilGPT-2)** – rychlé generování textů bez nutnosti API ✅ **Export do PDF** – možnost uložit generovaný obsah do souboru

## 📂 Struktura projektu

```
AdminAI/
│-- adminai.py       # Hlavní soubor aplikace
│-- adminai.db       # Databáze aplikace
│-- adminai_config.json # Konfigurační soubor
│-- log/             # Složka s logy aplikace
│-- README.md        # Tento soubor
```

## 🚀 Jak spustit aplikaci?

### 1️⃣ Požadavky

- **Python 3.8+**
- Knihovny (nainstaluj pomocí pip):
  ```bash
  pip install sqlite3 tkinter pandas matplotlib smtplib email json logging transformers textblob reportlab
  ```

### 2️⃣ Spuštění aplikace

```bash
python adminai.py
```

Aplikace se spustí v okně s grafickým rozhraním.

## 🛠️ Jak používat AdminAI?

### 📌 Správa schůzek

- Klikni na **"Naplánovat schůzku"** a vyplň údaje.
- Schůzky lze **upravit** nebo **smazat** kliknutím pravým tlačítkem.

### 📌 Správa úkolů

- Přidání úkolu přes **"Přidat úkol"**.
- Označení úkolu jako **dokončený** nebo jeho **smazání**.

### 📌 Generování obsahu s AI

- **E-maily:** "Generovat e-mail"
- **Příspěvky na FB:** "Generovat příspěvek na FB"
- **Obsah na web:** "Generovat obsah na web"
- **Export do PDF** nebo **kopírování do schránky**

### 📌 Statistiky a analýzy

- **"Zobrazit statistiky"** ukáže přehled schůzek a úkolů.
- **„Vygenerovat report"** vytvoří vizuální analýzu schůzek.

## 🔧 Konfigurace

Aplikace ukládá nastavení do **adminai\_config.json**. Můžeš zde změnit:

- SMTP server pro e-maily
- Archivní složku pro dokumenty
- Frekvenci připomenutí
- Téma aplikace (světlé/tmavé)

## 📌 Poznámky

Tento projekt je **lokální aplikace** – nevyžaduje připojení k API a všechny údaje jsou uloženy v **soukromé databázi**.

## 📞 Kontakt

lukas.drsticka@gmail.com 😊

