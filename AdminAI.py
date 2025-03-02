import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import os
from datetime import datetime, timedelta
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
import random
from transformers import GPT2LMHeadModel, GPT2Tokenizer
# Nový import pro PDF export
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Nastavení loggeru
logging.basicConfig(filename='adminai.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
class AdminAI:
    def __init__(self, root):
        self.root = root
        self.root.title("AdminAI - Personální Asistent")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Připojení k databázi
        self.setup_database()
        
        # Načtení konfigurace
        self.config = self.load_config()
        
        # Inicializace GPT-2 (použijeme distilgpt2 pro rychlost)
        self.tokenizer = GPT2Tokenizer.from_pretrained("distilgpt2")
        self.model = GPT2LMHeadModel.from_pretrained("distilgpt2")
        self.model.eval()
        logging.info("DistilGPT-2 model a tokenizer inicializovány")
        
        # Nastavení GUI
        self.setup_ui()
        
        # Spuštění časovače pro kontrolu připomenutí
        self.check_reminders()
        
        # Načtení učených vzorů z databáze
        self.load_learned_patterns()
        
        # Nastavení NLP - kombinace defaultních a učených vzorů
        self.nlp_patterns = {**self.default_patterns, **self.learned_patterns}
        
        # Uvítání
        self.display_output("AdminAI spuštěn s DistilGPT-2. Jak vám mohu dnes pomoci?")
        
        logging.info("AdminAI inicializován")

    def setup_database(self):
        """Inicializace databáze a přidání chybějících sloupců"""
        try:
            self.conn = sqlite3.connect('adminai.db')
            self.c = self.conn.cursor()
            
            self.c.execute('''CREATE TABLE IF NOT EXISTS meetings 
                        (id INTEGER PRIMARY KEY, date TEXT, time TEXT, participants TEXT, 
                        location TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            self.c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                        (id INTEGER PRIMARY KEY, task TEXT, deadline TEXT, priority TEXT, 
                        status TEXT DEFAULT 'pending', notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            self.c.execute('''CREATE TABLE IF NOT EXISTS emails 
                        (id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, subject TEXT, 
                        content TEXT, folder TEXT, status TEXT, 
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            self.c.execute('''CREATE TABLE IF NOT EXISTS user_data 
                        (key TEXT PRIMARY KEY, value TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            self.c.execute('''CREATE TABLE IF NOT EXISTS preferences 
                        (action TEXT, value TEXT, count INTEGER DEFAULT 1, 
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (action, value))''')
                        
            self.c.execute('''CREATE TABLE IF NOT EXISTS documents
                        (id INTEGER PRIMARY KEY, name TEXT, path TEXT, folder TEXT, 
                        tags TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                        
            self.c.execute('''CREATE TABLE IF NOT EXISTS reminders
                        (id INTEGER PRIMARY KEY, message TEXT, due_datetime TIMESTAMP, 
                        is_completed INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            self.add_missing_columns('meetings', ['location TEXT'])
            self.add_missing_columns('tasks', ['priority TEXT', 'status TEXT DEFAULT "pending"'])
            self.add_missing_columns('reminders', ['due_datetime TIMESTAMP'])
            self.add_missing_columns('preferences', ['count INTEGER DEFAULT 1'])
            
            default_user_data = {
                'name': 'Jan Novak',
                'email': 'jan.novak@example.com',
                'phone': '+420 123 456 789',
                'address': 'Praha 1',
                'company': 'Moje Firma s.r.o.',
                'position': 'Manažer'
            }
            
            for key, value in default_user_data.items():
                self.c.execute("INSERT OR IGNORE INTO user_data (key, value) VALUES (?, ?)", (key, value))
            
            self.conn.commit()
            logging.info("Databáze úspěšně inicializována")
        except sqlite3.Error as e:
            logging.error(f"Chyba při inicializaci databáze: {e}")
            messagebox.showerror("Chyba databáze", f"Nepodařilo se inicializovat databázi: {e}")

    def add_missing_columns(self, table_name, columns):
        """Přidání chybějících sloupců do tabulky"""
        try:
            self.c.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [column[1] for column in self.c.fetchall()]
            
            for column in columns:
                column_name = column.split()[0]
                if column_name not in existing_columns:
                    self.c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column}")
                    logging.info(f"Přidán sloupec {column_name} do tabulky {table_name}")
        except sqlite3.Error as e:
            logging.error(f"Chyba při přidávání sloupců do {table_name}: {e}")

    def load_config(self):
        """Načtení konfiguračního souboru"""
        default_config = {
            "email_server": "smtp.example.com",
            "email_port": 587,
            "email_username": "",
            "email_password": "",
            "archive_folder": "archiv",
            "reminder_check_interval": 60,
            "theme": "light",
            "language": "cs",
            "date_format": "%Y-%m-%d",
            "time_format": "%H:%M"
        }
        
        config_path = "adminai_config.json"
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            else:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            logging.error(f"Chyba při načítání konfigurace: {e}")
            return default_config

    def save_config(self):
        """Uložení konfigurace do souboru"""
        try:
            with open("adminai_config.json", 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logging.info("Konfigurace úspěšně uložena")
        except Exception as e:
            logging.error(f"Chyba při ukládání konfigurace: {e}")
    def setup_ui(self):
        """Nastavení uživatelského rozhraní"""
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        self.admin_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Funkce", menu=self.admin_menu)

        self.admin_menu.add_command(label="Naplánovat schůzku", command=lambda: self.plan_meeting())
        self.admin_menu.add_command(label="Spravovat e-maily", command=lambda: self.manage_emails())
        self.admin_menu.add_command(label="Vyplnit formulář", command=lambda: self.fill_form())
        self.admin_menu.add_command(label="Archivovat dokument", command=lambda: self.archive_document())
        self.admin_menu.add_command(label="Přidat úkol", command=lambda: self.plan_task())
        self.admin_menu.add_command(label="Vygenerovat report", command=lambda: self.generate_report())
        self.admin_menu.add_command(label="Generovat e-mail", command=lambda: self.generate_email())
        self.admin_menu.add_command(label="Generovat příspěvek na FB", command=lambda: self.generate_fb_post())
        self.admin_menu.add_command(label="Generovat obsah na web", command=lambda: self.generate_web_content())
        self.admin_menu.add_separator()
        self.admin_menu.add_command(label="Nastavit připomenutí", command=lambda: self.set_reminder())
        self.admin_menu.add_command(label="Zobrazit statistiky", command=lambda: self.show_statistics())

        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Zobrazit", menu=self.view_menu)
        
        self.view_menu.add_command(label="Seznam schůzek", command=lambda: self.show_items("meeting"))
        self.view_menu.add_command(label="Seznam úkolů", command=lambda: self.show_items("task"))
        self.view_menu.add_command(label="Seznam e-mailů", command=lambda: self.show_items("email"))
        self.view_menu.add_command(label="Seznam dokumentů", command=lambda: self.show_items("document"))
        self.view_menu.add_command(label="Seznam připomenutí", command=lambda: self.show_items("reminder"))

        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Nastavení", menu=self.settings_menu)
        
        self.settings_menu.add_command(label="Nastavení aplikace", command=self.open_settings)
        self.settings_menu.add_command(label="Upravit uživatelská data", command=self.edit_user_data)
        
        self.theme_menu = tk.Menu(self.settings_menu, tearoff=0)
        self.settings_menu.add_cascade(label="Téma", menu=self.theme_menu)
        self.theme_menu.add_command(label="Světlé", command=lambda: self.change_theme("light"))
        self.theme_menu.add_command(label="Tmavé", command=lambda: self.change_theme("dark"))

        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Nápověda", menu=self.help_menu)
        
        self.help_menu.add_command(label="O aplikaci", command=self.show_about)
        self.help_menu.add_command(label="Nápověda", command=self.show_help)

        self.input_frame = ttk.Frame(self.root, padding="10")
        self.input_frame.pack(fill=tk.X, padx=10, pady=5)

        self.entry_label = ttk.Label(self.input_frame, text="Zadej příkaz:")
        self.entry_label.pack(side=tk.LEFT, padx=5)
        
        self.entry = ttk.Entry(self.input_frame, width=60)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry.bind("<Return>", lambda event: self.process_command())
        
        self.button = ttk.Button(self.input_frame, text="Spustit", command=self.process_command)
        self.button.pack(side=tk.LEFT, padx=5)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.output_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.output_frame, text="Výstup")
        
        self.output_text = tk.Text(self.output_frame, height=15, width=70, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.scrollbar = ttk.Scrollbar(self.output_frame, command=self.output_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.config(yscrollcommand=self.scrollbar.set)
        
        self.tasks_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tasks_frame, text="Úkoly")
        
        self.tasks_treeview = ttk.Treeview(self.tasks_frame, columns=("task", "deadline", "priority", "status"), show="headings")
        self.tasks_treeview.heading("task", text="Úkol")
        self.tasks_treeview.heading("deadline", text="Termín")
        self.tasks_treeview.heading("priority", text="Priorita")
        self.tasks_treeview.heading("status", text="Stav")
        
        self.tasks_treeview.column("task", width=250)
        self.tasks_treeview.column("deadline", width=100)
        self.tasks_treeview.column("priority", width=80)
        self.tasks_treeview.column("status", width=80)
        
        self.tasks_scrollbar = ttk.Scrollbar(self.tasks_frame, command=self.tasks_treeview.yview)
        self.tasks_treeview.configure(yscrollcommand=self.tasks_scrollbar.set)
        
        self.tasks_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tasks_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tasks_treeview.bind("<Button-3>", self.show_task_context_menu)
        
        self.meetings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.meetings_frame, text="Schůzky")
        
        self.meetings_treeview = ttk.Treeview(self.meetings_frame, columns=("date", "time", "participants", "location"), show="headings")
        self.meetings_treeview.heading("date", text="Datum")
        self.meetings_treeview.heading("time", text="Čas")
        self.meetings_treeview.heading("participants", text="Účastníci")
        self.meetings_treeview.heading("location", text="Místo")
        
        self.meetings_treeview.column("date", width=100)
        self.meetings_treeview.column("time", width=80)
        self.meetings_treeview.column("participants", width=200)
        self.meetings_treeview.column("location", width=150)
        
        self.meetings_scrollbar = ttk.Scrollbar(self.meetings_frame, command=self.meetings_treeview.yview)
        self.meetings_treeview.configure(yscrollcommand=self.meetings_scrollbar.set)
        
        self.meetings_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.meetings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.meetings_treeview.bind("<Button-3>", self.show_meeting_context_menu)
        
        self.refresh_task_list()
        self.refresh_meeting_list()
        
        self.status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(5, 2))
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_text = ttk.Label(self.status_frame, text="AdminAI připraven")
        self.status_text.pack(side=tk.LEFT)
        
        self.status_clock = ttk.Label(self.status_frame, text="")
        self.status_clock.pack(side=tk.RIGHT)
        
        self.update_clock()
    def update_clock(self):
        """Aktualizace hodin ve stavové liště"""
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.status_clock.config(text=current_time)
        self.root.after(1000, self.update_clock)

    def display_output(self, message):
        """Zobrazí zprávu ve výstupním poli"""
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, message + "\n")
        logging.info(f"Výstup: {message}")

    def update_preference(self, action, value):
        """Aktualizace uživatelských preferencí a učení"""
        try:
            self.c.execute("SELECT count FROM preferences WHERE action=? AND value=?", (action, value))
            result = self.c.fetchone()
            if result:
                new_count = result[0] + 1
                self.c.execute("UPDATE preferences SET count=?, last_used=CURRENT_TIMESTAMP WHERE action=? AND value=?", 
                            (new_count, action, value))
            else:
                self.c.execute("INSERT INTO preferences (action, value, count, last_used) VALUES (?, ?, 1, CURRENT_TIMESTAMP)", 
                            (action, value))
            self.conn.commit()
            self.update_learned_patterns()
        except sqlite3.Error as e:
            logging.error(f"Chyba při aktualizaci preference: {e}")

    def get_preference(self, action, default):
        """Získání nejoblíbenější preference"""
        try:
            self.c.execute("SELECT value FROM preferences WHERE action=? ORDER BY count DESC LIMIT 1", (action,))
            result = self.c.fetchone()
            return result[0] if result else default
        except sqlite3.Error as e:
            logging.error(f"Chyba při získávání preference: {e}")
            return default

    def load_learned_patterns(self):
        """Načtení učených vzorů z databáze"""
        self.default_patterns = {
            r'(naplánuj|vytvoř|udělej)\s+schůzku': self.plan_meeting,
            r'(e-maily|emaily|mail)': self.manage_emails,
            r'(vyplň|vyplnit)\s+(formulář|formular)': self.fill_form,
            r'(archivuj|ulož)\s+(dokument|soubor)': self.archive_document,
            r'(přidej|vytvoř|nový)\s+(úkol|task)': self.plan_task,
            r'(vytvoř|generuj)\s+(přehled|report)': self.generate_report,
            r'připomeň': self.set_reminder,
            r'(statistik|analýz)': self.show_statistics,
            r'(co|seznam|ukaž)\s+(schůzk|úkol|meeting|task)': self.show_items,
            r'(jaké|jaký|co|seznam)\s+(mám|jsem|je)\s+schůzky\s+dnes': self.show_today_meetings,
            r'co\s+můžeš\s+udělat': self.show_help,
            r'ahoj|dobrý\s+den': self.greet_user,
            r'(co|jaké|jaký)\s+(umí|funkce|schopnosti|dovednosti)': self.list_capabilities,
            r'pošli\s+email': self.send_email,
            r'(nastav|zobraz)\s+připomenutí\s+pro\s+(\d{4}-\d{2}-\d{2})': self.set_or_show_reminder_by_date,
            r'(jak\s+se\s+máš|co\s+je\s+nového)': self.respond_to_general_question,
            r'(vytvoř|generuj)\s+e-?mail': self.generate_email,
            r'(vytvoř|generuj)\s+příspěvek\s+na\s+fb': self.generate_fb_post,
            r'(vytvoř|generuj)\s+obsah\s+na\s+web': self.generate_web_content,
        }
        self.learned_patterns = {}
        try:
            self.c.execute("SELECT action, value FROM preferences WHERE action LIKE 'command_%' ORDER BY count DESC")
            for action, value in self.c.fetchall():
                if 'command_' in action:
                    pattern = re.compile(value)
                    self.learned_patterns[pattern] = lambda x=None: self.handle_learned_command(value)
        except sqlite3.Error as e:
            logging.error(f"Chyba při načítání učených vzorů: {e}")

    def update_learned_patterns(self):
        """Aktualizace učených vzorů na základě nejčastěji používaných příkazů"""
        try:
            self.c.execute("SELECT value, count FROM preferences WHERE action LIKE 'command_%' ORDER BY count DESC LIMIT 5")
            learned_commands = self.c.fetchall()
            self.learned_patterns = {}
            for value, count in learned_commands:
                if count > 1:
                    pattern = re.compile(f"^{re.escape(value)}$")
                    self.learned_patterns[pattern] = lambda x=None, cmd=value: self.handle_learned_command(cmd)
            self.nlp_patterns = {**self.default_patterns, **self.learned_patterns}
            logging.info("Učené vzory aktualizovány")
        except sqlite3.Error as e:
            logging.error(f"Chyba při aktualizaci učených vzorů: {e}")

    def handle_learned_command(self, cmd):
        """Obsluha učeného příkazu"""
        self.display_output(f"Reaguji na učený příkaz: '{cmd}'. Jak vám mohu pomoci?")
        logging.info(f"Učený příkaz zpracován: {cmd}")

    def generate_text(self, prompt, max_length=100, temperature=0.7, top_k=50):
        """Generování textu pomocí DistilGPT-2"""
        try:
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt")
            output = self.model.generate(
                input_ids,
                max_length=max_length,
                temperature=temperature,
                top_k=top_k,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
            generated_text = self.tokenizer.decode(output[0], skip_special_tokens=True)
            return generated_text
        except Exception as e:
            logging.error(f"Chyba při generování textu GPT-2: {e}")
            return f"Chyba při generování: {e}"
    def create_edit_dialog(self, title, fields, callback, validation_func=None):
        """Dialogové okno pro úpravu parametrů s validací"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x300")
        dialog.grab_set()
        
        try:
            dialog.iconbitmap('adminai.ico')
        except:
            pass
        
        content_frame = ttk.Frame(dialog, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        entries = {}
        row = 0
        
        for label, default, field_type, options in fields:
            ttk.Label(content_frame, text=label).grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            
            if field_type == "entry":
                entry = ttk.Entry(content_frame, width=30)
                entry.insert(0, default)
                entry.grid(row=row, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
                entries[label] = entry
            
            elif field_type == "combobox":
                combo = ttk.Combobox(content_frame, values=options, width=28)
                combo.set(default)
                combo.grid(row=row, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
                entries[label] = combo
            
            elif field_type == "date":
                entry = ttk.Entry(content_frame, width=30)
                entry.insert(0, default)
                entry.grid(row=row, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
                
                cal_button = ttk.Button(content_frame, text="...", width=2, 
                                     command=lambda e=entry: self.select_date(e))
                cal_button.grid(row=row, column=2, padx=2, pady=5)
                entries[label] = entry
            
            elif field_type == "text":
                text_frame = ttk.Frame(content_frame)
                text_frame.grid(row=row, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
                
                scroll = ttk.Scrollbar(text_frame)
                text = tk.Text(text_frame, width=28, height=4, yscrollcommand=scroll.set)
                scroll.config(command=text.yview)
                
                text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scroll.pack(side=tk.RIGHT, fill=tk.Y)
                
                text.insert(tk.END, default)
                entries[label] = text
                
                row += 1
            
            row += 1
        
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Zrušit", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        def validate_and_submit():
            valid = True
            if validation_func:
                valid, message = validation_func(entries)
                if not valid:
                    messagebox.showerror("Chyba", message)
            
            if valid:
                callback(entries)
                dialog.destroy()
        
        ttk.Button(button_frame, text="Potvrdit", command=validate_and_submit).pack(side=tk.RIGHT, padx=5)
        
        list(entries.values())[0].focus_set()
        
        return dialog, entries

    def select_date(self, entry_widget):
        """Zobrazí kalendář pro výběr data"""
        try:
            from tkcalendar import Calendar
            
            date_dialog = tk.Toplevel(self.root)
            date_dialog.title("Vyberte datum")
            date_dialog.geometry("300x250")
            date_dialog.grab_set()
            
            try:
                current_date = datetime.strptime(entry_widget.get(), "%Y-%m-%d")
            except:
                current_date = datetime.now()
            
            cal = Calendar(date_dialog, selectmode='day', year=current_date.year, 
                        month=current_date.month, day=current_date.day, locale='cs_CZ')
            cal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            def set_date():
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, cal.get_date())
                date_dialog.destroy()
            
            ttk.Button(date_dialog, text="Vybrat", command=set_date).pack(pady=10)
            
        except ImportError:
            messagebox.showinfo("Informace", "Pro lepší výběr data nainstalujte modul tkcalendar: pip install tkcalendar")
    def open_settings(self):
        """Otevře nastavení aplikace"""
        def save_settings(entries):
            self.config["email_server"] = entries["SMTP server"].get()
            self.config["email_port"] = int(entries["SMTP port"].get())
            self.config["email_username"] = entries["E-mail"].get()
            self.config["email_password"] = entries["Heslo"].get()
            self.config["archive_folder"] = entries["Archivační složka"].get()
            self.config["reminder_check_interval"] = int(entries["Interval kontrol (s)"].get())
            self.config["date_format"] = entries["Formát datumu"].get()
            self.config["time_format"] = entries["Formát času"].get()
            
            self.save_config()
            self.display_output("Nastavení bylo úspěšně uloženo. Potřebujete další pomoc?")
        
        def validate_settings(entries):
            try:
                port = int(entries["SMTP port"].get())
                if port < 0 or port > 65535:
                    return False, "Port musí být číslo mezi 0 a 65535."
                
                interval = int(entries["Interval kontrol (s)"].get())
                if interval < 10:
                    return False, "Interval kontrol musí být alespoň 10 sekund."
                
                return True, ""
            except ValueError:
                return False, "SMTP port a interval kontrol musí být celá čísla."
        
        fields = [
            ("SMTP server", self.config["email_server"], "entry", None),
            ("SMTP port", str(self.config["email_port"]), "entry", None),
            ("E-mail", self.config["email_username"], "entry", None),
            ("Heslo", self.config["email_password"], "entry", None),
            ("Archivační složka", self.config["archive_folder"], "entry", None),
            ("Interval kontrol (s)", str(self.config["reminder_check_interval"]), "entry", None),
            ("Formát datumu", self.config["date_format"], "entry", None),
            ("Formát času", self.config["time_format"], "entry", None)
        ]
        
        self.create_edit_dialog("Nastavení aplikace", fields, save_settings, validate_settings)

    def edit_user_data(self):
        """Editace uživatelských dat"""
        try:
            self.c.execute("SELECT key, value FROM user_data")
            user_data = dict(self.c.fetchall())
            
            def save_user_data(entries):
                for label, entry in entries.items():
                    key = label.lower()
                    value = entry.get()
                    self.c.execute("UPDATE user_data SET value=?, last_updated=CURRENT_TIMESTAMP WHERE key=?", 
                                (value, key))
                
                self.conn.commit()
                self.display_output("Uživatelská data byla aktualizována. Můžu vám ještě pomoci?")
            
            fields = []
            for key in sorted(user_data.keys()):
                label = key.capitalize()
                fields.append((label, user_data.get(key, ""), "entry", None))
            
            self.create_edit_dialog("Editace uživatelských dat", fields, save_user_data)
            
        except sqlite3.Error as e:
            logging.error(f"Chyba při načítání uživatelských dat: {e}")
            messagebox.showerror("Chyba", f"Nepodařilo se načíst uživatelská data: {e}")

    def change_theme(self, theme_name):
        """Změna tématu aplikace"""
        try:
            if theme_name == "dark":
                self.root.configure(bg='#1e1e1e')
                style = ttk.Style()
                style.theme_use('clam')
                style.configure('TFrame', background='#1e1e1e')
                style.configure('TLabel', background='#1e1e1e', foreground='white')
                style.configure('TButton', background='#333333', foreground='white')
                style.configure('TNotebook', background='#1e1e1e')
                style.configure('TNotebook.Tab', background='#333333', foreground='white')
                self.output_text.configure(bg='#2d2d2d', fg='white', insertbackground='white')
            else:
                self.root.configure(bg='#f0f0f0')
                style = ttk.Style()
                style.theme_use('clam')
                style.configure('TFrame', background='#f0f0f0')
                style.configure('TLabel', background='#f0f0f0', foreground='black')
                style.configure('TButton', background='#e0e0e0', foreground='black')
                style.configure('TNotebook', background='#f0f0f0')
                style.configure('TNotebook.Tab', background='#e0e0e0', foreground='black')
                self.output_text.configure(bg='white', fg='black', insertbackground='black')
            
            self.config["theme"] = theme_name
            self.save_config()
            self.display_output(f"Téma změněno na: {theme_name}. Potřebujete další pomoc?")
        except Exception as e:
            logging.error(f"Chyba při změně tématu: {e}")
            messagebox.showerror("Chyba", f"Nepodařilo se změnit téma: {e}")

    def show_about(self):
        """Zobrazení informací o aplikaci"""
        about_text = """
        AdminAI - Personální Asistent
        Verze: 2.0 s DistilGPT-2
        
        Aplikace pro správu administrativních úkonů:
        - Plánování schůzek
        - Správa e-mailů
        - Vyplňování formulářů
        - Archivace dokumentů
        - Přidávání úkolů
        - Generování reportů
        - Připomenutí
        - Generování obsahu pomocí GPT-2
        
        © 2025 AdminAI Developers
        """
        messagebox.showinfo("O aplikaci", about_text)

    def show_help(self):
        """Zobrazení nápovědy a možností asistenta"""
        help_text = """
        AdminAI - Nápověda
        
        Aplikace podporuje následující příkazy:
        - 'Naplánovat schůzku' nebo 'vytvoř schůzku' - naplánuje novou schůzku
        - 'Přidat úkol' nebo 'nový úkol' - přidá nový úkol
        - 'Archivovat dokument' - archivuje dokument
        - 'Nastavit připomenutí' - nastaví časové upozornění
        - 'Vygenerovat report' - vygeneruje statistický přehled
        - 'Zobraz statistiky' - ukáže počet schůzek a úkolů
        - 'Jaké mám schůzky dnes' - zobrazí dnešní schůzky
        - 'Pošli email' - pošle e-mail
        - 'Vytvoř e-mail' - vygeneruje e-mail pomocí GPT-2 (kopírování nebo PDF)
        - 'Vytvoř příspěvek na FB' - vygeneruje příspěvek pro Facebook (kopírování nebo PDF)
        - 'Vytvoř obsah na web' - vygeneruje obsah pro web (TXT nebo PDF)
        - 'Zobraz připomenutí pro [datum]' - ukáže připomenutí pro konkrétní datum
        - 'Co můžeš udělat' - ukáže tuto nápovědu
        - 'Ahoj' nebo 'Dobrý den' - přivítání
        - 'Jak se máš?' nebo 'Co je nového?' - obecná konverzace
        
        Pro zadání příkazu můžete použít textové pole a stisknout Enter nebo kliknout na tlačítko 'Spustit'.
        """
        self.display_output(help_text)

    def greet_user(self):
        """Přivítání uživatele"""
        user_name = self.c.execute("SELECT value FROM user_data WHERE key='name'").fetchone()
        name = user_name[0] if user_name else "Uživateli"
        self.display_output(f"Ahoj, {name}! Jak vám mohu dnes pomoci?")

    def list_capabilities(self):
        """Vyjmenování funkcí asistenta"""
        capabilities = """
        Jsem AdminAI, váš personální asistent s DistilGPT-2. Umím následující:
        - Plánovat schůzky (např. 'naplánuj schůzku')
        - Přidávat úkoly (např. 'přidej úkol')
        - Archivovat dokumenty (např. 'archivuj dokument')
        - Nastavovat připomenutí (např. 'nastav připomenutí')
        - Generovat reporty (např. 'vytvoř report')
        - Zobrazovat statistiky (např. 'zobraz statistiky')
        - Zobrazovat dnešní schůzky (např. 'jaké mám schůzky dnes')
        - Posílat e-maily (např. 'pošli email')
        - Generovat e-maily pomocí GPT-2 (např. 'vytvoř e-mail', export do PDF)
        - Generovat příspěvky na Facebook pomocí GPT-2 (např. 'vytvoř příspěvek na FB', export do PDF)
        - Generovat obsah na web pomocí GPT-2 (např. 'vytvoř obsah na web', export do TXT/PDF)
        - Zobrazovat připomenutí pro konkrétní datum (např. 'zobraz připomenutí pro 2025-03-15')
        - Spravovat e-maily (zatím neimplementováno)
        - Vyplňovat formuláře (zatím neimplementováno)
        - Vítat uživatele (např. 'ahoj')
        - Odpovídat na obecné otázky (např. 'jak se máš?')
        - Učit se z vašich příkazů a přizpůsobovat se (automatické učení)
        
        Stačí zadat příkaz do vstupního pole a stisknout 'Spustit' nebo Enter.
        """
        self.display_output(capabilities.strip())

    def process_command(self):
        """Zpracování příkazu zadaného uživatelem"""
        command = self.entry.get().strip().lower()
        self.display_output(f"Zpracovávám příkaz: {command}")
        
        self.update_preference("command_" + command.split()[0], command)
        
        for pattern, action in self.nlp_patterns.items():
            if re.match(pattern, command):
                action()
                return
        
        responses = [
            "Promiň, nerozumím. Můžete mi říct, co potřebujete (např. 'naplánuj schůzku')?",
            "To mi není jasné. Zkuste prosím jiný příkaz, např. 'co můžeš udělat'.",
            "Nerozumím příkazu. Pomůžu vám s plánováním, úkoly nebo statistikami – co potřebujete?"
        ]
        self.display_output(random.choice(responses))
        logging.warning(f"Neznámý příkaz: {command}")
    def plan_meeting(self):
        """Naplánování nové schůzky"""
        def save_meeting(entries):
            date = entries["Datum"].get()
            time = entries["Čas"].get()
            participants = entries["Účastníci"].get()
            location = entries["Místo"].get()
            notes = entries["Poznámky"].get("1.0", tk.END).strip()
            
            try:
                self.c.execute("INSERT INTO meetings (date, time, participants, location, notes) VALUES (?, ?, ?, ?, ?)", 
                            (date, time, participants, location, notes))
                self.conn.commit()
                self.display_output("Schůzka byla úspěšně naplánována. Kdykoliv si můžete zobrazit seznam schůzek. Potřebujete další pomoc?")
                self.refresh_meeting_list()
            except sqlite3.Error as e:
                logging.error(f"Chyba při ukládání schůzky: {e}")
                messagebox.showerror("Chyba", f"Nepodařilo se uložit schůzku: {e}")
        
        def validate_meeting(entries):
            try:
                datetime.strptime(entries["Datum"].get(), "%Y-%m-%d")
                datetime.strptime(entries["Čas"].get(), "%H:%M")
                if not entries["Účastníci"].get().strip():
                    return False, "Účastníci nesmí být prázdní."
                return True, ""
            except ValueError:
                return False, "Datum musí být ve formátu RRRR-MM-DD a čas ve formátu HH:MM."
        
        fields = [
            ("Datum", datetime.now().strftime("%Y-%m-%d"), "date", None),
            ("Čas", datetime.now().strftime("%H:%M"), "entry", None),
            ("Účastníci", "", "entry", None),
            ("Místo", "", "entry", None),
            ("Poznámky", "", "text", None)
        ]
        
        self.create_edit_dialog("Naplánovat schůzku", fields, save_meeting, validate_meeting)
        self.display_output("Jaké schůzku byste chtěl/a naplánovat? Otevřel jsem dialog.")

    def manage_emails(self):
        """Správa e-mailů"""
        self.display_output("Funkce správy e-mailů ještě není plně implementována. Pracuji na tom!")
        logging.info("Správa e-mailů - placeholder")

    def fill_form(self):
        """Vyplnění formuláře"""
        self.display_output("Funkce vyplňování formulářů ještě není plně implementována. Brzy přidám tuto funkci!")
        logging.info("Vyplňování formulářů - placeholder")

    def archive_document(self):
        """Archivace dokumentu"""
        file_path = filedialog.askopenfilename(title="Vyberte dokument k archivaci")
        if file_path:
            filename = os.path.basename(file_path)
            folder = self.config["archive_folder"]
            if not os.path.exists(folder):
                os.makedirs(folder)
            dest_path = os.path.join(folder, filename)
            try:
                os.rename(file_path, dest_path)
                self.c.execute("INSERT INTO documents (name, path, folder, tags, notes) VALUES (?, ?, ?, ?, ?)", 
                            (filename, dest_path, folder, "", ""))
                self.conn.commit()
                self.display_output(f"Dokument {filename} byl úspěšně archivován do {folder}. Potřebujete další pomoc?")
            except Exception as e:
                logging.error(f"Chyba při archivaci dokumentu: {e}")
                messagebox.showerror("Chyba", f"Nepodařilo se archivovat dokument: {e}")

    def plan_task(self):
        """Přidání nového úkolu"""
        def save_task(entries):
            task = entries["Úkol"].get()
            deadline = entries["Termín"].get()
            priority = entries["Priorita"].get()
            notes = entries["Poznámky"].get("1.0", tk.END).strip()
            
            try:
                self.c.execute("INSERT INTO tasks (task, deadline, priority, status, notes) VALUES (?, ?, ?, ?, ?)", 
                            (task, deadline, priority, "pending", notes))
                self.conn.commit()
                self.display_output(f"Úkol '{task}' byl úspěšně přidán. Můžu vám ještě něco pomoci?")
                self.refresh_task_list()
            except sqlite3.Error as e:
                logging.error(f"Chyba při ukládání úkolu: {e}")
                messagebox.showerror("Chyba", f"Nepodařilo se uložit úkol: {e}")
        
        def validate_task(entries):
            try:
                datetime.strptime(entries["Termín"].get(), "%Y-%m-%d")
                if not entries["Úkol"].get().strip():
                    return False, "Úkol nesmí být prázdný."
                if entries["Priorita"].get() not in ["vysoká", "střední", "nízká"]:
                    return False, "Priorita musí být 'vysoká', 'střední' nebo 'nízká'."
                return True, ""
            except ValueError:
                return False, "Termín musí být ve formátu RRRR-MM-DD."
        
        fields = [
            ("Úkol", "", "entry", None),
            ("Termín", datetime.now().strftime("%Y-%m-%d"), "date", None),
            ("Priorita", "střední", "combobox", ["vysoká", "střední", "nízká"]),
            ("Poznámky", "", "text", None)
        ]
        
        self.create_edit_dialog("Přidat úkol", fields, save_task, validate_task)
        self.display_output("Jaký úkol byste chtěl/a přidat? Otevřel jsem dialog.")

    def generate_report(self):
        """Generování reportu"""
        try:
            self.c.execute("SELECT date, time FROM meetings WHERE date >= ?", 
                        (datetime.now().strftime("%Y-%m-%d"),))
            meetings = self.c.fetchall()
            
            dates = [m[0] for m in meetings]
            times = [m[1] for m in meetings]
            
            plt.figure(figsize=(10, 6))
            plt.plot(dates, times, marker='o')
            plt.title("Přehled schůzek")
            plt.xlabel("Datum")
            plt.ylabel("Čas")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(plt.gcf(), master=self.output_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
            
            self.display_output("Report byl vygenerován. Potřebujete další informace?")
            plt.close()
        except Exception as e:
            logging.error(f"Chyba při generování reportu: {e}")
            messagebox.showerror("Chyba", f"Nepodařilo se vygenerovat report: {e}")

    def set_reminder(self):
        """Nastavení připomenutí"""
        def save_reminder(entries):
            message = entries["Zpráva"].get()
            due_date = entries["Datum"].get()
            due_time = entries["Čas"].get()
            due_datetime = f"{due_date} {due_time}"
            
            try:
                self.c.execute("INSERT INTO reminders (message, due_datetime) VALUES (?, ?)", 
                            (message, due_datetime))
                self.conn.commit()
                self.display_output(f"Připomenutí '{message}' bylo nastaveno. Upozorním vás včas! Můžu vám ještě pomoci?")
                self.check_reminders()
            except sqlite3.Error as e:
                logging.error(f"Chyba při nastavování připomenutí: {e}")
                messagebox.showerror("Chyba", f"Nepodařilo se nastavit připomenutí: {e}")
        
        def validate_reminder(entries):
            try:
                datetime.strptime(f"{entries['Datum'].get()} {entries['Čas'].get()}", "%Y-%m-%d %H:%M")
                if not entries["Zpráva"].get().strip():
                    return False, "Zpráva připomenutí nesmí být prázdná."
                return True, ""
            except ValueError:
                return False, "Datum musí být ve formátu RRRR-MM-DD a čas ve formátu HH:MM."
        
        fields = [
            ("Zpráva", "", "entry", None),
            ("Datum", datetime.now().strftime("%Y-%m-%d"), "date", None),
            ("Čas", datetime.now().strftime("%H:%M"), "entry", None)
        ]
        
        self.create_edit_dialog("Nastavit připomenutí", fields, save_reminder, validate_reminder)
        self.display_output("Chcete nastavit připomenutí? Otevřel jsem dialog.")

    def check_reminders(self):
        """Kontrola a zobrazení připomenutí"""
        try:
            now = datetime.now()
            self.c.execute("SELECT id, message, due_datetime FROM reminders WHERE is_completed = 0")
            reminders = self.c.fetchall()
            
            for reminder in reminders:
                reminder_id, message, due_datetime = reminder
                due = datetime.strptime(due_datetime, "%Y-%m-%d %H:%M")
                if now >= due:
                    self.display_output(f"Připomenutí: {message}")
                    self.c.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
            
            self.conn.commit()
            self.root.after(self.config["reminder_check_interval"] * 1000, self.check_reminders)
        except Exception as e:
            logging.error(f"Chyba při kontrole připomenutí: {e}")

    def show_statistics(self):
        """Zobrazení statistik"""
        try:
            self.c.execute("PRAGMA table_info(tasks)")
            columns = [col[1] for col in self.c.fetchall()]
            
            self.c.execute("SELECT COUNT(*) FROM meetings WHERE date >= ?", 
                        (datetime.now().strftime("%Y-%m-%d"),))
            meeting_count = self.c.fetchone()[0]
            
            pending_tasks = 0
            if 'status' in columns:
                self.c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
                pending_tasks = self.c.fetchone()[0]
            else:
                pending_tasks = "Není dostupné (sloupec status chybí)"
            
            stats_text = f"Počet schůzek dnes: {meeting_count}\nPočet nevyřízených úkolů: {pending_tasks}"
            self.display_output(f"{stats_text} Potřebujete další statistiky?")
            logging.info(f"Statistiky zobrazeny: {stats_text}")
        except sqlite3.Error as e:
            logging.error(f"Chyba při zobrazení statistik: {e}")
            messagebox.showerror("Chyba", f"Nepodařilo se zobrazit statistiky: {e}")

    def show_items(self, item_type):
        """Zobrazení seznamu položek (schůzky, úkoly, atd.)"""
        if item_type == "meeting":
            self.c.execute("SELECT date, time, participants, location FROM meetings ORDER BY date, time")
            items = self.c.fetchall()
            self.meetings_treeview.delete(*self.meetings_treeview.get_children())
            for item in items:
                self.meetings_treeview.insert("", "end", values=item)
            self.display_output("Seznam schůzek aktualizován. Můžu vám s něčím jiným pomoci?")
        
        elif item_type == "task":
            self.c.execute("SELECT task, deadline, priority, status FROM tasks ORDER BY deadline")
            items = self.c.fetchall()
            self.tasks_treeview.delete(*self.tasks_treeview.get_children())
            for item in items:
                self.tasks_treeview.insert("", "end", values=item)
            self.display_output("Seznam úkolů aktualizován. Chcete něco upravit?")
        
        elif item_type == "email":
            self.display_output("Funkce zobrazení e-mailů ještě není implementována. Brzy ji přidám!")
        
        elif item_type == "document":
            self.c.execute("SELECT name, path, folder FROM documents ORDER BY created_at DESC")
            items = self.c.fetchall()
            self.display_output("Seznam dokumentů:\n" + "\n".join([f"{name} ({path})" for name, path, folder in items]) + "\nPotřebujete archivovat další dokument?")
        
        elif item_type == "reminder":
            self.c.execute("SELECT message, due_datetime FROM reminders WHERE is_completed = 0 ORDER BY due_datetime")
            items = self.c.fetchall()
            self.display_output("Seznam připomenutí:\n" + "\n".join([f"{msg} (do: {dt})" for msg, dt in items]) + "\nChcete nastavit další připomenutí?")
        
        logging.info(f"Zobrazen seznam: {item_type}")

    def show_today_meetings(self):
        """Zobrazení dnešních schůzek"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            self.c.execute("SELECT time, participants, location FROM meetings WHERE date = ?", (today,))
            meetings = self.c.fetchall()
            if meetings:
                output = "Dnešní schůzky:\n"
                for meeting in meetings:
                    output += f"{meeting[0]} - {meeting[1]} ({meeting[2]})\n"
                self.display_output(output + "Můžu vám ještě něco pomoci?")
            else:
                self.display_output("Dnes nemáte žádné schůzky. Chcete něco naplánovat?")
        except sqlite3.Error as e:
            self.display_output(f"Chyba při zobrazení schůzek: {e}")

    def send_email(self):
        """Posílání e-mailu"""
        def send_email_action(entries):
            recipient = entries["Příjemce"].get()
            subject = entries["Předmět"].get()
            content = entries["Zpráva"].get("1.0", tk.END).strip()
            
            try:
                msg = MIMEMultipart()
                msg['From'] = self.config["email_username"]
                msg['To'] = recipient
                msg['Subject'] = subject
                
                msg.attach(MIMEText(content, 'plain'))
                
                server = smtplib.SMTP(self.config["email_server"], self.config["email_port"])
                server.starttls()
                server.login(self.config["email_username"], self.config["email_password"])
                server.send_message(msg)
                server.quit()
                
                self.display_output(f"E-mail byl úspěšně odeslán na {recipient}. Potřebujete poslat další?")
                logging.info(f"E-mail odeslán na {recipient}")
            except Exception as e:
                logging.error(f"Chyba při odesílání e-mailu: {e}")
                messagebox.showerror("Chyba", f"Nepodařilo se odeslat e-mail: {e}")
        
        fields = [
            ("Příjemce", "", "entry", None),
            ("Předmět", "", "entry", None),
            ("Zpráva", "", "text", None)
        ]
        
        self.create_edit_dialog("Odeslat e-mail", fields, send_email_action)
        self.display_output("Chcete poslat e-mail? Otevřel jsem dialog.")

    def set_or_show_reminder_by_date(self, match):
        """Nastavení nebo zobrazení připomenutí pro konkrétní datum"""
        date_str = match.group(2)
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            
            self.c.execute("SELECT message, due_datetime FROM reminders WHERE is_completed = 0 AND date(due_datetime) = ?", (date_str,))
            reminders = self.c.fetchall()
            if reminders:
                output = f"Připomenutí pro {date_str}:\n"
                for msg, dt in reminders:
                    output += f"{msg} (v {dt[11:16]})\n"
                self.display_output(output + "Můžu vám ještě pomoci?")
            else:
                self.display_output(f"Pro {date_str} nemáte žádné připomenutí. Chcete nějaké nastavit?")
        except ValueError:
            self.display_output("Neplatné datum. Použijte formát RRRR-MM-DD.")
        except sqlite3.Error as e:
            self.display_output(f"Chyba při zobrazení připomenutí: {e}")

    def respond_to_general_question(self):
        """Odpovědi na obecné otázky"""
        responses = [
            "Mám se skvěle, děkuji za zájem! Jak vám mohu dnes pomoci?",
            "Všechno v pořádku, jsem připraven vám asistovat. Co potřebujete?",
            "Nic nového, jen čekám, až mi pomůžete s něčím zajímavým. Co mám udělat?"
        ]
        self.display_output(random.choice(responses))

    def refresh_task_list(self):
        """Obnovení seznamu úkolů"""
        try:
            self.c.execute("SELECT task, deadline, priority, status FROM tasks ORDER BY deadline")
            tasks = self.c.fetchall()
            self.tasks_treeview.delete(*self.tasks_treeview.get_children())
            for task in tasks:
                if len(task) == 4:
                    self.tasks_treeview.insert("", "end", values=task)
                else:
                    logging.warning(f"Nekompletní data úkolu: {task}")
            self.display_output("Seznam úkolů byl obnoven. Potřebujete něco přidat?")
        except sqlite3.Error as e:
            logging.error(f"Chyba při obnovování seznamu úkolů: {e}")
            messagebox.showerror("Chyba", f"Nepodařilo se obnovit seznam úkolů: {e}")

    def refresh_meeting_list(self):
        """Obnovení seznamu schůzek"""
        try:
            self.c.execute("SELECT date, time, participants, location FROM meetings ORDER BY date, time")
            meetings = self.c.fetchall()
            self.meetings_treeview.delete(*self.meetings_treeview.get_children())
            for meeting in meetings:
                self.meetings_treeview.insert("", "end", values=meeting)
            self.display_output("Seznam schůzek byl obnoven. Chcete naplánovat další schůzku?")
        except sqlite3.Error as e:
            logging.error(f"Chyba při obnovování seznamu schůzek: {e}")
            messagebox.showerror("Chyba", f"Nepodařilo se obnovit seznam schůzek: {e}")

    def show_task_context_menu(self, event):
        """Kontextové menu pro úkoly"""
        def mark_done():
            item = self.tasks_treeview.selection()[0]
            task = self.tasks_treeview.item(item, "values")[0]
            self.c.execute("UPDATE tasks SET status = 'done' WHERE task = ?", (task,))
            self.conn.commit()
            self.refresh_task_list()
            self.display_output(f"Úkol '{task}' označen jako dokončen. Můžu vám ještě pomoci?")
        
        def delete_task():
            item = self.tasks_treeview.selection()[0]
            task = self.tasks_treeview.item(item, "values")[0]
            if messagebox.askyesno("Potvrzení", f"Opravdu chcete smazat úkol '{task}'?"):
                self.c.execute("DELETE FROM tasks WHERE task = ?", (task,))
                self.conn.commit()
                self.refresh_task_list()
                self.display_output(f"Úkol '{task}' byl smazán. Potřebujete něco dalšího?")
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Označit jako dokončené", command=mark_done)
        menu.add_command(label="Smazat", command=delete_task)
        menu.post(event.x_root, event.y_root)

    def show_meeting_context_menu(self, event):
        """Kontextové menu pro schůzky"""
        def delete_meeting():
            item = self.meetings_treeview.selection()[0]
            date = self.meetings_treeview.item(item, "values")[0]
            if messagebox.askyesno("Potvrzení", f"Opravdu chcete smazat schůzku z {date}?"):
                self.c.execute("DELETE FROM meetings WHERE date = ?", (date,))
                self.conn.commit()
                self.refresh_meeting_list()
                self.display_output(f"Schůzka z {date} byla smazána. Chcete naplánovat novou?")
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Smazat", command=delete_meeting)
        menu.post(event.x_root, event.y_root)
    def generate_email(self):
        """Generování e-mailu pomocí DistilGPT-2 s exportem do PDF"""
        def generate_and_show(entries):
            name = entries["Jméno příjemce"].get()
            recipient = entries["E-mail příjemce"].get()
            product = entries["Produkt"].get()
            description = entries["Popis"].get("1.0", tk.END).strip()
            temperature = float(entries["Kreativita"].get())
            firma = self.c.execute("SELECT value FROM user_data WHERE key='company'").fetchone()[0]
            
            prompt = f"Napiš formální e-mail pro {name} od firmy {firma} o novém produktu {product}. Popis produktu: {description}"
            generated_text = self.generate_text(prompt, max_length=200, temperature=temperature)
            
            email_dialog = tk.Toplevel(self.root)
            email_dialog.title("Vygenerovaný e-mail (GPT-2)")
            email_dialog.geometry("500x400")
            
            email_text = tk.Text(email_dialog, wrap=tk.WORD)
            email_text.insert(tk.END, generated_text)
            email_text.pack(fill=tk.BOTH, expand=True)
            
            def copy_to_clipboard():
                self.root.clipboard_clear()
                self.root.clipboard_append(email_text.get("1.0", tk.END).strip())
                self.display_output("E-mail byl zkopírován do schránky.")
                email_dialog.destroy()
            
            def save_to_pdf():
                file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF soubory", "*.pdf")])
                if file_path:
                    c = canvas.Canvas(file_path, pagesize=letter)
                    c.setFont("Helvetica", 12)
                    text_obj = c.beginText(40, 750)
                    for line in email_text.get("1.0", tk.END).strip().split("\n"):
                        text_obj.textLine(line)
                    c.drawText(text_obj)
                    c.showPage()
                    c.save()
                    self.display_output(f"E-mail byl uložen jako PDF do {file_path}.")
                    email_dialog.destroy()
            
            button_frame = ttk.Frame(email_dialog)
            button_frame.pack(side=tk.BOTTOM, pady=10)
            ttk.Button(button_frame, text="Kopírovat do schránky", command=copy_to_clipboard).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Uložit jako PDF", command=save_to_pdf).pack(side=tk.LEFT, padx=5)
        
        fields = [
            ("Jméno příjemce", "", "entry", None),
            ("E-mail příjemce", "", "entry", None),
            ("Produkt", "", "entry", None),
            ("Popis", "", "text", None),
            ("Kreativita", "0.7", "entry", None)
        ]
        
        self.create_edit_dialog("Generovat e-mail (GPT-2)", fields, generate_and_show)
        self.display_output("Chcete vygenerovat e-mail pomocí GPT-2? Otevřel jsem dialog.")

    def generate_fb_post(self):
        """Generování příspěvku na Facebook pomocí DistilGPT-2 s exportem do PDF"""
        def generate_and_show(entries):
            product = entries["Produkt"].get()
            description = entries["Popis"].get("1.0", tk.END).strip()
            temperature = float(entries["Kreativita"].get())
            firma = self.c.execute("SELECT value FROM user_data WHERE key='company'").fetchone()[0]
            
            prompt = f"Napiš krátký a poutavý příspěvek na Facebook od firmy {firma} o novém produktu {product}. Popis: {description}"
            generated_text = self.generate_text(prompt, max_length=100, temperature=temperature)
            
            fb_dialog = tk.Toplevel(self.root)
            fb_dialog.title("Vygenerovaný příspěvek na FB (GPT-2)")
            fb_dialog.geometry("500x200")
            
            fb_text = tk.Text(fb_dialog, wrap=tk.WORD)
            fb_text.insert(tk.END, generated_text)
            fb_text.pack(fill=tk.BOTH, expand=True)
            
            def copy_to_clipboard():
                self.root.clipboard_clear()
                self.root.clipboard_append(fb_text.get("1.0", tk.END).strip())
                self.display_output("Příspěvek byl zkopírován do schránky.")
                fb_dialog.destroy()
            
            def save_to_pdf():
                file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF soubory", "*.pdf")])
                if file_path:
                    c = canvas.Canvas(file_path, pagesize=letter)
                    c.setFont("Helvetica", 12)
                    text_obj = c.beginText(40, 750)
                    for line in fb_text.get("1.0", tk.END).strip().split("\n"):
                        text_obj.textLine(line)
                    c.drawText(text_obj)
                    c.showPage()
                    c.save()
                    self.display_output(f"Příspěvek byl uložen jako PDF do {file_path}.")
                    fb_dialog.destroy()
            
            button_frame = ttk.Frame(fb_dialog)
            button_frame.pack(side=tk.BOTTOM, pady=10)
            ttk.Button(button_frame, text="Kopírovat do schránky", command=copy_to_clipboard).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Uložit jako PDF", command=save_to_pdf).pack(side=tk.LEFT, padx=5)
        
        fields = [
            ("Produkt", "", "entry", None),
            ("Popis", "", "text", None),
            ("Kreativita", "0.7", "entry", None)
        ]
        
        self.create_edit_dialog("Generovat příspěvek na FB (GPT-2)", fields, generate_and_show)
        self.display_output("Chcete vygenerovat příspěvek na FB pomocí GPT-2? Otevřel jsem dialog.")

    def generate_web_content(self):
        """Generování obsahu na web pomocí DistilGPT-2 s exportem do PDF"""
        def generate_and_show(entries):
            topic = entries["Téma"].get()
            content = entries["Obsah"].get("1.0", tk.END).strip()
            temperature = float(entries["Kreativita"].get())
            firma = self.c.execute("SELECT value FROM user_data WHERE key='company'").fetchone()[0]
            
            prompt = f"Napiš článek pro web od firmy {firma} na téma {topic}. Úvodní informace: {content}"
            generated_text = self.generate_text(prompt, max_length=300, temperature=temperature)
            
            web_dialog = tk.Toplevel(self.root)
            web_dialog.title("Vygenerovaný obsah na web (GPT-2)")
            web_dialog.geometry("500x400")
            
            web_text = tk.Text(web_dialog, wrap=tk.WORD)
            web_text.insert(tk.END, generated_text)
            web_text.pack(fill=tk.BOTH, expand=True)
            
            def save_to_file():
                file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Textové soubory", "*.txt")])
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(web_text.get("1.0", tk.END).strip())
                    self.display_output(f"Obsah byl uložen do {file_path}.")
                    web_dialog.destroy()
            
            def save_to_pdf():
                file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF soubory", "*.pdf")])
                if file_path:
                    c = canvas.Canvas(file_path, pagesize=letter)
                    c.setFont("Helvetica", 12)
                    text_obj = c.beginText(40, 750)
                    for line in web_text.get("1.0", tk.END).strip().split("\n"):
                        text_obj.textLine(line)
                    c.drawText(text_obj)
                    c.showPage()
                    c.save()
                    self.display_output(f"Obsah byl uložen jako PDF do {file_path}.")
                    web_dialog.destroy()
            
            button_frame = ttk.Frame(web_dialog)
            button_frame.pack(side=tk.BOTTOM, pady=10)
            ttk.Button(button_frame, text="Uložit do souboru", command=save_to_file).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Uložit jako PDF", command=save_to_pdf).pack(side=tk.LEFT, padx=5)
        
        fields = [
            ("Téma", "", "entry", None),
            ("Obsah", "", "text", None),
            ("Kreativita", "0.7", "entry", None)
        ]
        
        self.create_edit_dialog("Generovat obsah na web (GPT-2)", fields, generate_and_show)
        self.display_output("Chcete vygenerovat obsah na web pomocí GPT-2? Otevřel jsem dialog.")
if __name__ == "__main__":
    root = tk.Tk()
    app = AdminAI(root)
    root.mainloop()
