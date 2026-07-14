# Kovets Maker

Éditeur web statique de couvertures 6 × 9 pouces pour des kovtsim de si'hot et maamarim.

## Lancer localement

Depuis ce dossier :

```powershell
python -m http.server 4173
```

Puis ouvrir `http://localhost:4173`.

## Déploiement

L’application ne nécessite ni compilation ni serveur applicatif. Le dossier peut être déployé tel quel sur Netlify, Vercel, GitHub Pages ou tout hébergement statique.

## Fonctions disponibles

- édition RTL en direct de tous les blocs de la première page ;
- choix du cadre et activation globale de l’en-tête fixe ;
- formules d’attribution et années de publication prédéfinies ;
- champs distincts pour l’éditeur, la rue, la ville et la commémoration ;
- choix du logo Kehot ou import d’un logo PNG, JPG, WebP ou SVG ;
- redimensionnement automatique des lignes longues ;
- sauvegarde locale automatique dans le navigateur ;
- zoom responsive ;
- export d’un véritable PDF 6 × 9 pouces construit à partir de la première page originale.

La première page du PDF fourni sert directement de gabarit. Le cadre, le logo Kehot et tous les textes non modifiables restent donc dans le PDF avec leurs ressources et fontes d’origine. Seules les zones personnalisables sont masquées puis remplacées lors de l’export.

## Fontes des zones personnalisables

Les fontes `PDF JNarkis Rebuilt` et `PDF JDavid Rebuilt` sont reconstruites à partir des sous-ensembles embarqués dans les premières pages des quatre couvertures fournies. Les CID/GID étant stables entre les documents, leurs vrais contours peuvent être fusionnés sans redessiner les lettres.

- Narkis gras : alphabet couvert sauf `ג`, `ך` et `ץ` ;
- Narkis régulier : alphabet couvert sauf `ג`, `ז`, `ך`, `ף` et `ץ` ;
- chiffres d’adresse Narkis : `0` et `7` repris de la sous-fonte originale ;
- David régulier : alphabet couvert sauf `ך`, `ן`, `ף` et `ץ` ;
- David gras : les lettres nécessaires à `חלק א` et `חלק ב` sont couvertes.

Lorsqu’un contour reste absent, le navigateur utilise automatiquement Narkiss Yair, puis David Libre. Le détail généré se trouve dans `assets/fonts/pdf-font-coverage.json`.

Les outils de diagnostic et de reconstruction sont conservés dans `tools/analyze_pdf_cover_fonts.py` et `tools/rebuild_cover_fonts.py`.
