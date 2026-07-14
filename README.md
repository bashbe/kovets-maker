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
- export SVG autonome avec polices incorporées ;
- export PNG 1800 × 2700 pixels, correspondant à 6 × 9 pouces à 300 ppp.

L’ornement vectoriel et le logo Kehot proviennent de la première page du PDF de référence fourni pour ce projet.

Les textes non modifiables utilisent les sous-ensembles `JBilna`, `JName` et `JNarkis` intégrés à cette page. Leurs tables Unicode ont été reconstruites uniquement pour les glyphes fixes présents dans la couverture ; les champs libres conservent donc des fontes complètes.
