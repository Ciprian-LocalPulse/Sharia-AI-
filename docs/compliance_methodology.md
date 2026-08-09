# Metodologie de Conformitate Sharia

Acest document explică, la nivel de principiu, logica implementată în
modulele `screening` și `zakat`, precum și limitările sale. Este scris
pentru un public tehnic și non-tehnic deopotrivă (dezvoltatori, analiști
de conformitate, membri ai unui comitet Sharia).

## 1. Screening de echitate (`screening/equity_screener.py`)

Procesul urmează structura pe două etape folosită de indicii islamici
majori (DJIM, FTSE Shariah, S&P Shariah):

### 1.1 Screening calitativ (de activitate/business)

O companie este exclusă dacă activitatea sa principală se încadrează
într-un sector considerat haram — listat în `EXCLUDED_SECTORS`
(alcool, jocuri de noroc, bănci/asigurări convenționale, carne de porc,
divertisment pentru adulți, tutun, armament controversat, media imorală).

Această listă este **intenționat editabilă**: diferite comitete Sharia
adoptă interpretări ușor diferite (ex: unele exclud tutunul strict, altele
îl clasifică drept makruh sever, dar nu absolut haram).

### 1.2 Screening cantitativ (rate financiare)

Chiar și o companie cu activitate permisă poate fi neconformă dacă
structura sa financiară implică expunere semnificativă la dobândă (riba).
Se verifică trei rate, fiecare raportată la capitalizarea bursieră:

| Rată | Prag implicit | Raționament |
|---|---|---|
| Datorie purtătoare de dobândă / cap. bursieră | 33% | Limitează expunerea structurală la finanțare bazată pe dobândă. |
| Numerar + depozite purtătoare de dobândă / cap. bursieră | 33% | Limitează venitul pasiv din dobândă deținut ca lichiditate. |
| Creanțe comerciale / cap. bursieră | 49% | Limitează expunerea la instrumente asimilabile datoriei (vânzare de creanțe). |

Pragul de 33% provine din interpretarea clasică a unei treimi ("thuluth")
ca limită a ceea ce este considerat "minoritar/nesemnificativ" (*al-aqall*)
într-un context financiar mixt — o euristică juridică, nu o formulă exactă.

### 1.3 Purificare a venitului (income purification)

Dacă o companie este altfel conformă, dar are un procent mic de venit din
surse neconforme (ex: dobândă incidentală la depozite bancare), sub pragul
de excludere (implicit 5%), investitorii sunt sfătuiți convențional să
"purifice" acel procent din dividendele primite — adică să-l doneze
caritabil, nu să-l consume. `ScreeningResult.purification_ratio` calculează
automat acest procent.

## 2. Detecție riba/gharar/maysir în contracte (`nlp/riba_detector.py`)

### 2.1 De ce lexical, nu doar ML

Un motor pur lexical (bazat pe listă de termeni) are dezavantajul evident
al recall-ului limitat — nu recunoaște parafraze sau formulări indirecte.
Are însă un avantaj esențial pentru context reglementat: **este determinist
și complet auditabil**. Fiecare semnalare (`Flag`) indică exact ce termen
a fost găsit, în ce propoziție, cu ce nivel de încredere predefinit.
Pentru un comitet Sharia sau un auditor, această trasabilitate este
adesea mai valoroasă decât un scor de "black box" de la un model ML.

De aceea arhitectura este **hibridă**: stratul lexical rulează întotdeauna
ca prim filtru; un model ML (opțional, conectabil prin
`RibaClassifierProtocol`) poate fi adăugat pentru acoperire semantică
suplimentară, dar nu înlocuiește stratul de bază.

### 2.2 Cele trei categorii de risc

- **Riba** (دبا) — dobândă/interes, sub orice formă (simplă, compusă,
  penalizări de întârziere calculate procentual în timp).
- **Gharar** (غرر) — incertitudine sau ambiguitate excesivă în obiectul
  contractului (preț nedeterminat, cantitate necunoscută, vânzarea unui
  bun pe care vânzătorul nu îl deține).
- **Maysir** (ميسر) — speculație pură/joc de noroc, unde câștigul unei
  părți depinde exclusiv de șansă, fără o contribuție economică reală.

### 2.3 Provocări specifice limbii arabe

Araba atașează prepoziții și conjuncții direct la substantive, fără
spațiu (clitic-e): "بفائدة" (cu dobândă) = "ب" + "فائدة". Un matching
naiv pe substring produce atât **falși negativi** (nu recunoaște
"بفائدة" ca variantă a "فائدة") cât și **falși pozitivi** periculoși
(termenul "ربا" apare ca substring în interiorul cuvântului complet
diferit "الأرباح" — profituri). Toolkit-ul rezolvă ambele probleme prin
tokenizare pe cuvinte întregi + generare de variante fără clitic-e
(`clitic_variants()`), nu prin căutare brută de substring. Vezi
`tests/test_riba_detector.py` pentru cazurile de regresie exacte.

## 3. Calcul Zakat (`zakat/zakat_calculator.py`)

Implementarea urmează interpretarea clasică majoritară:

- **Rata**: 2.5% din averea netă eligibilă.
- **Nisab**: pragul minim de avere sub care Zakat nu este obligatoriu,
  calculat dinamic pe baza prețului curent al aurului (85g) sau argintului
  (595g). Implicit se folosește pragul mai mic dintre cele două (convenție
  favorabilă beneficiarilor Zakat, larg acceptată).
- **Active eligibile**: numerar, creanțe cu șanse rezonabile de încasare,
  inventar comercial (la valoare de piață), investiții conforme Sharia,
  aur/argint.
- **Deduceri**: datorii scadente pe termen scurt.

**Limitare cunoscută**: calculul nu acoperă cazuri complexe precum zakat
pe active mixte pe termen lung, zakat agricol, zakat pe efective de
animale sau situații de parteneriat cu proporții de proprietate neclare —
acestea necesită consultanță Sharia dedicată.

## 4. Ce NU face acest toolkit

- Nu emite fatwa și nu constituie aviz juridic islamic.
- Nu garantează conformitate legală/reglementară într-o anumită
  jurisdicție (ex: cerințele unei bănci centrale pot diferi de
  interpretarea Sharia aplicată aici).
- Nu înlocuiește revizuirea umană a unui comitet Sharia acreditat pentru
  decizii de investiție sau structurare de produse financiare.
