# AdminAI - Personální Asistent

## 📌 Popis projektu
AdminAI je inteligentní **administrativní asistent**, který pomáhá s řízením pracovních úkolů, schůzek, připomenutí a e-mailů. Nabízí jednoduché **grafické rozhraní (GUI)** postavené na **Tkinteru**, umožňuje správu databáze SQLite a integraci s e-mailovým serverem.

Tento asistent je určen **manažerům, zaměstnancům i freelancerům**, kteří chtějí efektivně řídit svůj pracovní den.

---

## ⚡ Hlavní funkce
- 📅 **Plánování schůzek** – přidávání, editace a mazání schůzek v databázi
- ✅ **Správa úkolů** – přidávání úkolů, nastavování priorit a sledování jejich stavu
- 🔔 **Připomenutí** – možnost nastavit upozornění na důležité události
- ✉️ **Správa e-mailů** – odesílání e-mailů pomocí SMTP serveru
- 📂 **Archivace dokumentů** – ukládání souborů do předdefinované složky
- 📊 **Statistiky a reporty** – analýza naplánovaných schůzek a úkolů
- 🏠 **Přizpůsobení aplikace** – možnost změnit konfiguraci, téma nebo uživatelská data
- 🔍 **Automatické učení vzorců chování** – asistent si pamatuje časté příkazy a přizpůsobuje se

---

## 🛠 Technologie
- **Python** – hlavní programovací jazyk
- **Tkinter** – GUI rozhraní
- **SQLite** – databázová správa
- **Matplotlib** – generování grafických statistik
- **Pandas** – práce s daty
- **smtplib** – odesílání e-mailů
- **JSON** – konfigurace aplikace
- **Logging** – ukládání logů pro debugging

---

## 🔧 Instalace
1. **Naklonuj repozitář** nebo stáhni soubor `AdminAI6.py`
2. Ujisti se, že máš nainstalované následující knihovny:
   ```bash
   pip install pandas matplotlib tkcalendar
   ```
3. **Spusť aplikaci**:
   ```bash
   python AdminAI6.py
   ```

---

## 🚀 Použití
### Ovládání přes GUI
Po spuštění aplikace se zobrazí **grafické rozhraní**, kde můžeš:
- **Spravovat schůzky** a úkoly pomocí menu
- **Zadávat příkazy** do textového pole (např. „Naplánuj schůzku“)
- **Zobrazit statistiky** o schůzkách a úkolech

### Příkazy asistenta
AdminAI rozpoznává textové příkazy:
- **„Naplánuj schůzku“** → otevře dialog pro přidání schůzky
- **„Přidej úkol“** → přidá nový úkol s prioritou
- **„Jaké mám schůzky dnes?“** → zobrazí dnešní schůzky
- **„Pošli email“** → otevře dialog pro odeslání e-mailu
- **„Nastav připomenutí“** → vytvoří upozornění

---

## 📝 Konfigurace
Aplikace ukládá nastavení v souboru **`adminai_config.json`**, kde lze změnit například:
- SMTP server pro e-maily
- Výchozí složku pro archivaci
- Interval kontroly připomenutí

Pokud tento soubor neexistuje, aplikace ho **automaticky vytvoří**.

---

## 📈 Statistiky a reporty
Aplikace umožňuje vizuální přehled naplánovaných schůzek a úkolů:
- Zobrazuje **graf** s rozložením schůzek
- Sčítá počet dokončených a nedokončených úkolů
- Generuje tabulkové přehledy přímo v GUI

---

## 🔗 Další možnosti
- **Změna tématu** aplikace (světlé/tmavé)
- **Kontextová nabídka** (pravé kliknutí) pro editaci úkolů a schůzek
- **Automatické učení příkazů** – AdminAI si pamatuje často používané příkazy

---

## 🏆 Autor
Tento projekt vyvinul **Lukáš Drštička** v rámci vývoje **AI agentů**. Pokud máš dotazy nebo chceš vylepšení, můžeš se ozvat na **lukas.drsticka@gmail.com**.

---

## 📌 Závěr
AdminAI je **praktický nástroj**, který ti usnadní každodenní pracovní úkoly a zlepší organizaci. 🚀

Chceš vylepšení? Máš nápad na novou funkci? **Neváhej přispět!** 😊
