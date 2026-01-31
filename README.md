🔒 Samba Control Center v2.0
Samba Control Center je moderní webové rozhraní postavené na Flasku, které slouží k administraci Samba (SMB/CIFS) sdílení, správe uživatelů a připojování síťových disků v Linuxových systémech. Zapomeňte na ruční úpravy /etc/samba/smb.conf nebo /etc/fstab.

✨ Hlavní funkce
📂 Správa sdílení: Snadné přidávání a odstraňování Samba sekcí s možností nastavení oprávnění (RW/RO), přístupu hostů a masek souborů.

👥 Správa uživatelů: Integrovaný management Samba uživatelů (přidávání přes smbpasswd, kontrola existujících Unix uživatelů).

🔌 Mount Manager: Pokročilé rozhraní pro správu /etc/fstab. Podporuje automatické generování souborů s přihlašovacími údaji (credentials) pro bezpečné ukládání hesel.

🛡️ Protokolový volič: Rychlé přepínání mezi verzemi SMB (1.0, 2.1, 3.0) pro zajištění kompatibility se staršími NAS nebo moderními Windows servery.

⚙️ Systémové nástroje:

Restartování služby smbd přímo z prohlížeče.

Validace konfigurace pomocí testparm.

Automatické zálohování konfiguračních souborů s časovým razítkem.

Aplikování změn v fstab pomocí mount -a.

📸 Design
Aplikace disponuje moderním "Glassmorphism" UI s temným režimem, který je plně responzivní a využívá:

Font IBM Plex Sans pro vysokou čitelnost.

Ikony Font Awesome 6.

Interaktivní prvky a modální okna pro čistý uživatelský zážitek.

🚀 Instalace a spuštění
Prerekvizity
Aplikace vyžaduje Linuxový systém s nainstalovaným Samba serverem a práva uživatele root (pro zápis do /etc).

Bash
# Instalace Samba a Python závislostí (příklad pro Debian/Ubuntu)
sudo apt update
sudo apt install samba samba-common-bin python3 python3-flask
Stažení a spuštění
Stáhněte soubor samba_control_center.py na svůj server.

Spusťte jej s právy root:

Bash
sudo python3 samba_control_center.py
Otevřete prohlížeč a přejděte na adresu: http://vasedresa:5000 (aplikace automaticky zkusí porty 5000, 5001, 5050 nebo 8000, pokud jsou obsazené).

📂 Struktura souborů
Aplikace pracuje s následujícími systémovými cestami:

/etc/samba/smb.conf - Hlavní konfigurace Samby.

/etc/samba/backups/ - Automatické zálohy konfigurace.

/etc/samba/credentials/ - Bezpečně uložené přihlašovací údaje pro síťové mounty (chmod 600).

/etc/fstab - Správa trvalých síťových disků.

⚠️ Bezpečnostní upozornění
Tento nástroj je určen pro interní správu. Nikdy jej nevystavujte přímo do veřejného internetu bez dalšího zabezpečení (VPN, reverzní proxy s autentizací jako Nginx, atd.).

Aplikace běží standardně jako root, aby mohla modifikovat systémové soubory.

🛠️ Technologie
Backend: Python 3, Flask

Frontend: HTML5, CSS3 (CSS proměnné, flexbox/grid), Vanilla JavaScript

Systém: Subprocess API pro interakci s Linuxovými utilitami (systemctl, mount, pdbedit, smbpasswd).
