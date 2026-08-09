# Roadmap

## v0.1 (curent — alpha)

- [x] Screening de echitate bazat pe reguli AAOIFI/DJIM configurabile
- [x] Detector lexical riba/gharar/maysir pentru arabă, offline, cu
      gestionare corectă a clitic-elor și fără falsuri pozitive pe
      omonime cunoscute (ex: ربا vs. الأرباح)
- [x] Calculator Zakat cu Nisab dinamic (aur/argint)
- [x] Pipeline de orchestrare end-to-end + export JSON auditabil
- [x] API REST (FastAPI) cu documentație interactivă
- [x] Suită de teste unitare (16 teste, 100% offline, stdlib)

## v0.2 (planificat)

- [ ] **Autentificare API** — API keys / OAuth2 pentru expunere multi-tenant
- [ ] **Model ML pentru scoring semantic** — integrare AraBERT/CAMeLBERT
      fine-tuned prin `RibaClassifierProtocol`, cu set de date de
      antrenament adnotat de juriști
- [ ] **Suport Sukuk** — screening de conformitate pentru structuri de
      obligațiuni islamice (Ijara, Murabaha, Mudaraba Sukuk)
- [ ] **Suport Takaful** — modul dedicat pentru asigurări islamice
      (separare fond participanți / fond operator)
- [ ] **Export PDF** — rapoarte de conformitate formatate profesional,
      pentru arhivare/audit extern

## v0.3 (explorare)

- [ ] Dashboard web (React) pentru vizualizarea rapoartelor de conformitate
- [ ] Conectori pentru burse din regiunea MENA (Tadawul, DFM, ADX) —
      ingestie automată de date financiare pentru screening batch
- [ ] Suport multi-limbă pentru interfața de raportare (arabă, engleză,
      franceză)
- [ ] Bibliotecă extinsă de clauze contractuale adnotate (open dataset)
      pentru cercetare academică în NLP juridic arab

## Principii care ghidează prioritizarea

1. Explicabilitatea nu se sacrifică niciodată pentru acoperire mai mare.
2. Orice funcționalitate nouă legată de interpretare Sharia necesită
   review din partea unui contribuitor cu background în jurisprudență
   islamică sau citarea unei surse metodologice recunoscute.
3. Nucleul rămâne utilizabil offline — dependențele grele (modele ML,
   servicii cloud) sunt întotdeauna opționale, niciodată obligatorii.

## Cum propui o schimbare de prioritate

Deschide un GitHub Issue cu eticheta `roadmap`, descriind problema de
business pe care o rezolvă și, dacă e relevant, referința metodologică.
