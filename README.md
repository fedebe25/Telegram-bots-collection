# 🤖 Suite di Bot Telegram Professionali

Benvenuto nella repository ufficiale dei bot Telegram modulari. Questa raccolta è progettata per offrire soluzioni pronte all'uso, stabili e ad alte prestazioni per la gestione di community, automazioni e utilità quotidiane.

## 📑 Indice dei Bot della Repository

Clicca su uno dei bot sottostanti per saltare direttamente alla sezione di tuo interesse o esplorare la cartella dedicata:

- 👉 **[Bot 0-A: Il Guardiano del Gruppo](#-bot-0-a-il-guardiano-del-gruppo)** _(Stai visualizzando questo bot)_
- 👉 **[Bot 0-B: Il Bot Risposte Automatiche (FAQ Bot)](#)** _(Disponibile nella cartella `0b_faq_bot`)_
- 👉 **[Bot 0-C: L'Inoltratore Semplice (Mirror Bot)](#)** _(Disponibile nella cartella `0c_mirror_bot`)_
- 👉 **[Bot 0-D: Il Convertitore di file (PDF & Media)](#)** _(Disponibile nella cartella `0-d_converter_bot`)_
- 👉 **[Bot 0-E: Il Bot Scadenze e Reminder](#)** _(Disponibile nella cartella `0-e_reminder_bot`)_

---

# 🛡️ Bot 0-A: Il Guardiano del Gruppo (Antispam & Welcome)

> **Un guardiano automatico per i tuoi gruppi Telegram:** blocca lo spam all'ingresso, filtra i messaggi indesiderati, gestisce i warn e protegge la community H24 senza alcuno sforzo manuale.

## 📋 Panoramica Generale

I gruppi Telegram con più membri vengono regolarmente presi d'assalto da bot di spam automatizzati che entrano, postano link truffaldini o pubblicità e spariscono. **Il Guardiano del Gruppo** risolve radicalmente questo problema intercettando i nuovi ingressi, bloccando preventivamente la chat ai nuovi arrivati e obbligandoli a una verifica umana rapida e intuitiva.

Oltre all'antispam in ingresso, il bot include un sistema completo di moderazione interna: **anti-flood**, **filtro per parole vietate e link**, **sistema di avvertimenti (warn)** e **canale log privato** per gli amministratori.

---

## ✨ Funzionalità Principali

1. **🔒 Mute Preventivo e Verifica Umana (Captcha Inline)**
   - Non appena un utente entra, viene **silenziato preventivamente** (impedendogli di inviare qualsiasi messaggio o spam).
   - Il bot invia un messaggio di benvenuto con un pulsante interattivo: _"✅ Clicca qui per dimostrare che sei umano"_.
   - Se l'utente clicca in tempo, i permessi vengono ripristinati automaticamente e il messaggio di servizio viene ripulito dalla chat.

2. **⏱️ Timer di Sicurezza e Azione Configurabile (`/set_timeout`)**
   - Se l'utente non clicca entro 60 secondi, scatta un'azione automatica configurabile direttamente tramite comando in chat:
     - **`kick`**: l'utente viene rimosso dal gruppo.
     - **`mute`**: l'utente resta bloccato in sola lettura finché un admin non lo sblocca manualmente.

3. **📢 Canale Log Privato Dedicato**
   - Tutte le azioni importanti (rimozioni, interventi anti-flood, filtri violati, warn) vengono registrate in tempo reale su un canale Telegram privato riservato agli amministratori, permettendo di monitorare la salute del gruppo da qualsiasi dispositivo.

4. **⚠️ Sistema di Avvertimenti (Warn System) con `/warn`**
   - Gli admin possono ammonire gli utenti rispondendo a un loro messaggio con il comando `/warn`.
   - Al raggiungimento della soglia (3 ammonizioni), il bot applica automaticamente una sanzione (es. mute temporaneo di 15 minuti) e azzera il contatore.

5. **🛑 Filtro Intelligente per Parole Vietate e Link**
   - **Filtro Link:** attivabile con `/filter_links on`, cancella all'istante qualsiasi link o invito non autorizzato.
   - **Filtro Parole:** gli admin possono aggiungere o rimuovere termini sgradevoli tramite `/filter_word_add` e `/filter_word_remove`. I messaggi offensivi vengono rimossi all'istante.

6. **⚡ Sistema Anti-Flood Automatico**
   - Riconosce e blocca gli utenti che inviano troppi messaggi in pochissimi secondi, applicando un mute temporaneo automatico per evitare il fastidioso flood in chat.

7. **👑 Whitelist Globale ed Extra per Gruppo**
   - Gli amministratori e gli utenti inseriti nella whitelist (tramite ID o tramite i comandi `/whitelist_add` e `/whitelist_remove`) sono completamente esentati da controlli, captcha e filtri.

---

## 🛠️ Comandi Disponibili per gli Admin

| Comando                        | Descrizione                                                               |
| :----------------------------- | :------------------------------------------------------------------------ |
| `/set_timeout <kick/mute>`     | Imposta l'azione da compiere alla scadenza del timer di verifica.         |
| `/warn`                        | Rispondi a un messaggio per ammonire l'utente (3 warn = mute automatico). |
| `/whitelist_add`               | Aggiunge un utente alla whitelist del gruppo (tramite risposta o ID).     |
| `/whitelist_remove`            | Rimuove un utente dalla whitelist del gruppo.                             |
| `/whitelist_list`              | Mostra la lista degli utenti in whitelist extra per il gruppo.            |
| `/filter_links <on/off>`       | Attiva o disattiva il blocco automatico dei link.                         |
| `/filter_word_add <parola>`    | Aggiunge una parola al filtro dei termini vietati.                        |
| `/filter_word_remove <parola>` | Rimuove una parola dal filtro dei termini vietati.                        |

---

## ⚙️ Configurazione e Installazione

1. Clona la repository e naviga nella cartella del bot.
2. Installa le dipendenze richieste:
   ```bash
   pip install python-telegram-bot python-dotenv
   ```
