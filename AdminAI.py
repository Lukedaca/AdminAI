import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import os
from datetime import datetime

# Připojení k databázi
conn = sqlite3.connect('adminai.db')
c = conn.cursor()

# Vytvoření tabulek
c.execute('''CREATE TABLE IF NOT EXISTS meetings 
             (date TEXT, time TEXT, participants TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS emails 
             (sender TEXT, subject TEXT, content TEXT, folder TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tasks 
             (task TEXT, deadline TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_data 
             (key TEXT, value TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS preferences 
             (action TEXT, value TEXT, count INTEGER)''')
conn.commit()

# Simulace uživatelských dat
c.execute("INSERT OR IGNORE INTO user_data VALUES ('name', 'Jan Novak')")
c.execute("INSERT OR IGNORE INTO user_data VALUES ('address', 'Praha 1')")
conn.commit()

# Funkce pro aktualizaci preferencí
def update_preference(action, value):
    c.execute("SELECT count FROM preferences WHERE action=? AND value=?", (action, value))
    result = c.fetchone()
    if result:
        new_count = result[0] + 1
        c.execute("UPDATE preferences SET count=? WHERE action=? AND value=?", (new_count, action, value))
    else:
        c.execute("INSERT INTO preferences VALUES (?, ?, ?)", (action, value, 1))
    conn.commit()

# Funkce pro získání nejoblíbenější preference
def get_preference(action, default):
    c.execute("SELECT value FROM preferences WHERE action=? ORDER BY count DESC LIMIT 1", (action,))
    result = c.fetchone()
    return result[0] if result else default

# Dialogové okno pro úpravu parametrů
def create_edit_dialog(title, fields, callback):
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("300x200")
    dialog.grab_set()  # Zaměří okno

    entries = {}
    for i, (label, default) in enumerate(fields.items()):
        tk.Label(dialog, text=label).grid(row=i, column=0, padx=5, pady=5)
        entry = tk.Entry(dialog)
        entry.insert(0, default)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entries[label] = entry
    
    tk.Button(dialog, text="Potvrdit", command=lambda: [callback(entries), dialog.destroy()]).grid(row=len(fields), column=0, columnspan=2, pady=10)

# Funkce pro plánování schůzek
def plan_meeting(command=None):
    def save_meeting(entries):
        date = entries["Datum"].get()
        time = entries["Čas"].get()
        participants = entries["Účastníci"].get()
        
        c.execute("SELECT * FROM meetings WHERE date=? AND time=?", (date, time))
        if c.fetchone() is None:
            c.execute("INSERT INTO meetings VALUES (?, ?, ?)", (date, time, participants))
            update_preference("meeting_time", time)
            update_preference("meeting_participants", participants)
            conn.commit()
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Schůzka naplánována na {date} v {time} s {participants}.")
        else:
            messagebox.showerror("Chyba", "Termín je obsazen.")

    if command:
        parts = command.lower().split()
        date = "2025-02-26" if "středu" in parts else datetime.now().strftime("%Y-%m-%d")
        time = parts[parts.index("v") + 1] if "v" in parts else get_preference("meeting_time", "10:00")
        participants = parts[parts.index("s") + 1] if "s" in parts else get_preference("meeting_participants", "tým")
        save_meeting({"Datum": tk.Entry(root, text=date), "Čas": tk.Entry(root, text=time), "Účastníci": tk.Entry(root, text=participants)})
    else:
        fields = {
            "Datum": datetime.now().strftime("%Y-%m-%d"),
            "Čas": get_preference("meeting_time", "10:00"),
            "Účastníci": get_preference("meeting_participants", "tým")
        }
        create_edit_dialog("Naplánovat schůzku", fields, save_meeting)

# Funkce pro správu e-mailů
def manage_emails(command=None):
    def save_emails(entries):
        sender = entries["Odesílatel"].get()
        folder = entries["Složka"].get()
        c.execute("INSERT INTO emails VALUES (?, ?, ?, ?)", (sender, "Předmět", "Obsah e-mailu", folder))
        update_preference("email_folder", folder)
        conn.commit()
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"E-maily od {sender} přesunuty do složky {folder}.")

    if command:
        parts = command.lower().split()
        if "roztřiď" in parts and "e-maily" in parts:
            sender = parts[parts.index("od") + 1] if "od" in parts else "neznámý"
            folder = parts[parts.index("do") + 1] if "do" in parts else get_preference("email_folder", "ostatní")
            save_emails({"Odesílatel": tk.Entry(root, text=sender), "Složka": tk.Entry(root, text=folder)})
        elif "odpověz" in parts:
            sender = parts[parts.index("na") + 1] if "na" in parts else "neznámý"
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Odpověď odeslána na e-mail od {sender}: 'Děkuji, brzy se ozvu.'")
    else:
        fields = {
            "Odesílatel": "šéf",
            "Složka": get_preference("email_folder", "ostatní")
        }
        create_edit_dialog("Spravovat e-maily", fields, save_emails)

# Funkce pro vyplňování formulářů
def fill_form(command=None):
    def save_form(entries):
        name = entries["Jméno"].get()
        address = entries["Adresa"].get()
        form_content = f"Jméno: {name}\nAdresa: {address}\nDatum: {datetime.now().strftime('%Y-%m-%d')}"
        with open("formular.txt", "w", encoding="utf-8") as f:
            f.write(form_content)
        update_preference("form_filled", "yes")
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, "Formulář vyplněn a uložen jako 'formular.txt'.")

    c.execute("SELECT value FROM user_data WHERE key='name'")
    name = c.fetchone()[0]
    c.execute("SELECT value FROM user_data WHERE key='address'")
    address = c.fetchone()[0]
    
    if command:
        save_form({"Jméno": tk.Entry(root, text=name), "Adresa": tk.Entry(root, text=address)})
    else:
        fields = {"Jméno": name, "Adresa": address}
        create_edit_dialog("Vyplnit formulář", fields, save_form)

# Funkce pro archivaci dokumentů
def archive_document(command=None):
    def save_document(entries):
        folder = entries["Složka"].get()
        file_path = filedialog.askopenfilename(title="Vyber dokument k archivaci")
        if file_path:
            dest_folder = f"archiv/{folder}"
            os.makedirs(dest_folder, exist_ok=True)
            os.rename(file_path, f"{dest_folder}/{os.path.basename(file_path)}")
            update_preference("archive_folder", folder)
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Dokument uložen do složky '{folder}'.")
        else:
            messagebox.showerror("Chyba", "Žádný dokument nevybrán.")

    if command:
        parts = command.lower().split()
        folder = parts[parts.index("do") + 1] if "do" in parts else get_preference("archive_folder", "ostatní")
        save_document({"Složka": tk.Entry(root, text=folder)})
    else:
        fields = {"Složka": get_preference("archive_folder", "ostatní")}
        create_edit_dialog("Archivovat dokument", fields, save_document)

# Funkce pro plánování úkolů
def plan_task(command=None):
    def save_task(entries):
        task = entries["Úkol"].get()
        deadline = entries["Termín"].get()
        c.execute("INSERT INTO tasks VALUES (?, ?)", (task, deadline))
        update_preference("task_deadline", deadline)
        conn.commit()
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"Úkol přidán: '{task}' s termínem {deadline}.")

    if command:
        parts = command.lower().split()
        task = " ".join(parts[parts.index("úkol:") + 1:parts.index("do")]) if "úkol:" in parts else "neznámý úkol"
        deadline = parts[parts.index("do") + 1] if "do" in parts else get_preference("task_deadline", "pátek")
        save_task({"Úkol": tk.Entry(root, text=task), "Termín": tk.Entry(root, text=deadline)})
    else:
        fields = {
            "Úkol": "Odeslat fakturu",
            "Termín": get_preference("task_deadline", "pátek")
        }
        create_edit_dialog("Přidat úkol", fields, save_task)

# Funkce pro generování reportů
def generate_report(command=None):
    c.execute("SELECT * FROM meetings")
    meetings = c.fetchall()
    report_content = "Přehled schůzek:\n"
    for date, time, participants in meetings:
        report_content += f"- {date} v {time}: {participants}\n"
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write(report_content)
    update_preference("report_generated", "meetings")
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, "Report schůzek vygenerován jako 'report.txt'.")

# Hlavní funkce pro zpracování příkazů z textového pole
def process_command():
    command = entry.get()
    if "naplánuj schůzku" in command.lower():
        plan_meeting(command)
    elif "e-maily" in command.lower() or "odpověz" in command.lower():
        manage_emails(command)
    elif "vyplň formulář" in command.lower():
        fill_form(command)
    elif "archivuj dokument" in command.lower():
        archive_document(command)
    elif "přidej úkol" in command.lower():
        plan_task(command)
    elif "vytvoř přehled" in command.lower():
        generate_report(command)
    else:
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, "Nerozumím příkazu. Zkus to znovu.")

# Funkce pro tlačítka v menu
def button_action(func):
    func()

# GUI
root = tk.Tk()
root.title("AdminAI")
root.geometry("600x400")

# Menu
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

admin_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Funkce", menu=admin_menu)

admin_menu.add_command(label="Naplánovat schůzku", command=lambda: button_action(plan_meeting))
admin_menu.add_command(label="Spravovat e-maily", command=lambda: button_action(manage_emails))
admin_menu.add_command(label="Vyplnit formulář", command=lambda: button_action(fill_form))
admin_menu.add_command(label="Archivovat dokument", command=lambda: button_action(archive_document))
admin_menu.add_command(label="Přidat úkol", command=lambda: button_action(plan_task))
admin_menu.add_command(label="Vygenerovat report", command=lambda: button_action(generate_report))

# Textové pole pro příkaz
entry_label = tk.Label(root, text="Zadej příkaz (nebo použij menu):")
entry_label.pack(pady=5)
entry = tk.Entry(root, width=60)
entry.pack(pady=5)

# Tlačítko pro spuštění příkazu
button = tk.Button(root, text="Spustit příkaz", command=process_command)
button.pack(pady=10)

# Výstupní text
output_text = tk.Text(root, height=15, width=70)
output_text.pack(pady=10)

# Spuštění aplikace
root.mainloop()

# Uzavření databáze
conn.close()