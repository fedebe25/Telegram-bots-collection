# 🤖 Suite di Bot Telegram Professionali

Benvenuto nella repository ufficiale dei bot Telegram su misura. Ogni bot in questa raccolta è un modulo pronto all'uso, pensato per risolvere un problema concreto di community management, automazione o produttività — e personalizzabile su richiesta per esigenze specifiche.

Ogni bot vive nella sua cartella dedicata, con configurazione indipendente: puoi installarne uno solo, alcuni, o tutti insieme sullo stesso server.

## 📑 Indice dei Bot della Repository

- 👉 **[Bot 0-A: Il Guardiano del Gruppo](#-bot-0-a-il-guardiano-del-gruppo)** — Antispam, verifica ingressi e moderazione automatica _(cartella `0a_guardian_bot`)_
- 👉 **[Bot 0-B: Il Bot Risposte Automatiche (FAQ Bot)](#)** — Risponde automaticamente alle domande frequenti della community _(cartella `0b_faq_bot`)_
- 👉 **[Bot 0-C: L'Inoltratore Semplice (Mirror Bot)](#)** — Sincronizza contenuti tra canali e gruppi _(cartella `0c_mirror_bot`)_
- 👉 **[Bot 0-D: Il Convertitore di File (PDF & Media)](#)** — Conversione file al volo dentro la chat _(cartella `0d_converter_bot`)_
- 👉 **[Bot 0-E: Il Bot Scadenze e Reminder](#)** — Promemoria e scadenze programmate per team e gruppi _(cartella `0e_reminder_bot`)_

---

# 🛡️ Bot 0-A: Il Guardiano del Gruppo

> **Un moderatore automatico H24 per il tuo gruppo Telegram.** Blocca lo spam all'ingresso con una verifica anti-bot, filtra link e parole indesiderate, gestisce gli avvertimenti e — su richiesta — riconosce i tentativi di truffa più sofisticati con un livello di analisi basato su intelligenza artificiale.

## 📋 A chi serve

Qualsiasi community Telegram con più di poche decine di membri prima o poi affronta lo stesso problema: account spam che entrano, postano link truffaldini o pubblicità non richiesta, e spariscono prima che un admin se ne accorga. Moderare a mano non è sostenibile, soprattutto per chi gestisce il gruppo nel tempo libero.

**Il Guardiano del Gruppo** automatizza l'intera pipeline di difesa: dal controllo all'ingresso alla moderazione continua dei messaggi, fino alla gestione degli utenti problematici — il tutto configurabile in tempo reale, senza mai toccare una riga di codice.

---

## ✨ Funzionalità Principali

1. **🔒 Mute Preventivo + Verifica Anti-Bot con CAPTCHA Matematico**
   Ogni nuovo utente viene silenziato nell'istante stesso in cui entra, prima ancora di poter scrivere un solo messaggio. Il bot gli propone un semplice calcolo matematico da risolvere entro 60 secondi tramite pulsanti — una barriera leggera per un umano, ma sufficiente a bloccare la stragrande maggioranza degli account spam automatizzati.

2. **⚙️ Pannello di Controllo Interattivo (`/settings`)**
   Nessun comando da imparare a memoria: gli admin gestiscono ogni impostazione del gruppo tramite un pannello a bottoni diretto in chat — filtri, azione di timeout, tutto attivabile/disattivabile con un tocco, con conferma visiva immediata (🟢 ON / 🔴 OFF).

3. **⏱️ Azione Automatica alla Scadenza del Timer**
   Se l'utente non completa la verifica in tempo, scatta automaticamente una delle due azioni configurate dall'admin:
   - **Kick**: l'utente viene rimosso dal gruppo (può rientrare in futuro).
   - **Mute**: l'utente resta in sola lettura finché un admin non lo sblocca manualmente.

4. **📢 Canale Log Privato + Notifica Admin**
   Ogni intervento importante — rimozioni, mute per flood, ammonizioni al limite — viene registrato in tempo reale su un canale Telegram privato dedicato, consultabile da qualsiasi dispositivo e condivisibile con altri admin. In caso di rimozione automatica, l'admin principale riceve anche una notifica diretta in privato.

5. **⚠️ Sistema di Ammonizioni (`/warn`)**
   Gli admin possono ammonire un utente rispondendo a un suo messaggio. Al raggiungimento di 3 ammonizioni, il bot applica automaticamente un mute temporaneo e azzera il contatore — nessun intervento manuale richiesto.

6. **🛑 Filtri di Moderazione Configurabili**
   Attivabili singolarmente dal pannello `/settings`:
   - **Filtro Link** — elimina automaticamente messaggi contenenti URL o inviti non autorizzati.
   - **Filtro Inoltri (Forward)** — blocca i messaggi rimbalzati da altri canali/gruppi.
   - **Blocco Messaggi da Canale** — impedisce a canali collegati anonimamente di scrivere nel gruppo.
   - **Filtro Parole Vietate** — blacklist personalizzabile per gruppo tramite `/filter_word_add` e `/filter_word_remove`.

7. **🧠 Filtro Anti-Spam potenziato da AI (opzionale)**
   Per i messaggi più ambigui (che contengono termini a rischio come "crypto", "investimento", "bonus"...), il bot può interrogare un modello di intelligenza artificiale (Google Gemini) per valutare se si tratta di un vero tentativo di truffa prima di eliminarlo — riducendo drasticamente i falsi positivi rispetto a un filtro basato solo su parole chiave.
   _Il filtro AI è completamente opzionale, richiede una chiave API fornita dal gestore del bot, ed è protetto da un tetto massimo di utilizzo mensile configurabile — nessun costo a sorpresa._

8. **⚡ Anti-Flood Automatico**
   Rileva utenti che inviano troppi messaggi in pochi secondi (comportamento tipico di spam bot o raid) e applica un mute temporaneo automatico, senza intervento admin.

9. **👑 Whitelist a Doppio Livello**
   - **Whitelist globale**: ID esenti su tutti i gruppi in cui il bot opera, impostati alla configurazione iniziale.
   - **Whitelist per gruppo**: gestibile in autonomia dagli admin con `/whitelist_add` e `/whitelist_remove` (rispondendo al messaggio dell'utente, o specificando l'ID).
   - Gli amministratori del gruppo sono sempre esentati automaticamente, senza bisogno di configurazione.

---

## 🛠️ Comandi Disponibili per gli Admin

| Comando                        | Descrizione                                                                  |
| :----------------------------- | :--------------------------------------------------------------------------- |
| `/settings`                    | Apre il pannello di controllo interattivo con tutti i filtri del gruppo.     |
| `/warn`                        | Rispondi al messaggio di un utente per ammonirlo (3 warn = mute automatico). |
| `/whitelist_add`               | Esenta un utente dai controlli (rispondendo al suo messaggio o via ID).      |
| `/whitelist_remove`            | Rimuove un utente dalla whitelist del gruppo.                                |
| `/filter_word_add <parola>`    | Aggiunge una parola alla blacklist del gruppo.                               |
| `/filter_word_remove <parola>` | Rimuove una parola dalla blacklist del gruppo.                               |

Tutti gli altri comportamenti (filtro link, filtro inoltri, blocco canali, filtro AI, azione di timeout kick/mute) si gestiscono dal pannello `/settings`, senza bisogno di comandi testuali.

---

## 🏗️ Architettura Tecnica

- **Persistenza dati**: database SQLite locale (nessun servizio esterno da pagare o configurare), con impostazioni salvate **per singolo gruppo** — lo stesso bot può gestire più community con comportamenti diversi.
- **Motore asincrono**: costruito su `python-telegram-bot`, gestisce in parallelo verifiche, filtri e comandi senza rallentamenti anche su gruppi molto attivi.
- **Logging professionale**: registro eventi su file (con rotazione automatica) e console, per diagnosi e audit.
- **Zero dipendenze a pagamento obbligatorie**: il bot funziona al 100% delle sue funzioni core senza alcun costo. L'unica componente opzionale a pagamento (filtro AI) richiede una chiave fornita e gestita dal cliente stesso.

---

## ⚙️ Configurazione e Installazione

1. Clona la repository e naviga nella cartella `0a_guardian_bot`.

2. Installa le dipendenze richieste:

   ```bash
   pip install python-telegram-bot python-dotenv aiosqlite
   pip install "python-telegram-bot[job-queue]"
   ```

   Per abilitare il filtro AI opzionale (Google Gemini):

   ```bash
   pip install google-genai
   ```

3. Copia `.env.example` in `.env` e compila le variabili (vedi tabella sotto).

4. Crea il bot con [@BotFather](https://t.me/BotFather), **disattiva la Privacy Mode** (Bot Settings → Group Privacy → Turn off), e aggiungi il bot al gruppo come **amministratore** (necessario per silenziare/rimuovere utenti e cancellare messaggi).

5. Avvia il bot:
   ```bash
   python main.py
   ```

### Variabili d'ambiente

| Variabile                    | Descrizione                                                    | Obbligatoria |
| :--------------------------- | :------------------------------------------------------------- | :----------- |
| `TELEGRAM_BOT_TOKEN`         | Token del bot ottenuto da BotFather.                           | Sì           |
| `ADMIN_CHAT_ID`              | ID Telegram dell'admin, per le notifiche private di rimozione. | No           |
| `LOG_CHANNEL_ID`             | ID del canale privato dove inviare i log delle azioni del bot. | No           |
| `WHITELIST_IDS`              | ID separati da virgola, esenti su tutti i gruppi.              | No           |
| `DB_FILE`                    | Percorso del file database (default: `bot_database.db`).       | No           |
| `LOG_FILE`                   | Percorso del file di log (default: `bot.log`).                 | No           |
| `GEMINI_API_KEY`             | Chiave API per il filtro AI opzionale (Google Gemini).         | No           |
| `GEMINI_MODEL`               | Modello Gemini da usare (default: `gemini-2.5-flash-lite`).    | No           |
| `GEMINI_MAX_CALLS_PER_MONTH` | Tetto massimo di chiamate AI al mese (default: `1000`).        | No           |

> 💡 **Nota sul filtro AI**: se `GEMINI_API_KEY` non è impostata, il bot funziona regolarmente con tutti gli altri filtri attivi — il pannello `/settings` segnalerà semplicemente che l'opzione AI non è disponibile finché non viene configurata una chiave.

---

## 🧾 Note per chi acquista questo bot

- Il bot va eseguito su un server sempre attivo (locale, VPS o servizio di hosting a scelta) per garantire una copertura continua H24.
- Ogni gruppo gestito ha impostazioni indipendenti: puoi usare lo stesso bot su più community senza conflitti.
- Il costo del bot è **una tantum**: nessun abbonamento, nessuna commissione ricorrente legata al suo funzionamento base.
