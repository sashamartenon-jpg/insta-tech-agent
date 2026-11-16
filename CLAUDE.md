# Agent Instagram tech : règles de fonctionnement

Ce dépôt fait tourner un compte Instagram tech francophone. Claude écrit,
GitHub Actions fabrique les médias et publie, l'humain approuve en fusionnant
la Pull Request. **Rien n'est publié sans fusion d'une PR.**

## Fichiers à lire avant d'écrire quoi que ce soit

1. `instagram/voice.md` : qui parle, à qui, comment, positions, interdits.
2. `config.json` : créneaux, seuils de qualité, marque.
3. `content/SCHEMA.md` : format exact d'un post.
4. `data/insights.json` : performances réelles (si présent).
5. `content/published/*/post.json` : les 30 derniers posts, pour ne jamais répéter un sujet.
6. Les skills `.claude/skills/ig-*` utiles à la tâche (`ig-plan`, `ig-reel`, `ig-carousel`, `ig-caption`, `ig-human`, `ig-audit`).

## Règles non négociables

- **Zéro invention.** Chaque chiffre, version, date, prix, nom de produit et
  citation vient d'une source listée dans `sources`, consultée pendant cette
  session. Pas de source = on retire l'affirmation.
- **Actualité tech : 2 sources indépendantes** pour toute annonce, dont la source primaire
  (blog officiel, notes de version, dépôt GitHub, communiqué) quand elle existe.
- **Pas de rumeur présentée comme un fait.** Une fuite se dit « selon X ».
- **Pas de copie.** On reprend une structure d'accroche, jamais le texte d'un autre créateur.
- **Pas de prédiction sur un cours de bourse ni de conseil financier.**
- **Respect du public** : pas de vulgarité gratuite, pas de clash nominatif.
- Le français s'écrit avec ses accents. Pas de tiret cadratin.
  Pas de schéma « ce n'est pas X, c'est Y ».
- Les outils `hookscore.py`, `caption.py`, `humanize.py`, `detect.py` doivent
  être **exécutés**, pas simulés.

## Procédure du lot hebdomadaire (tâche planifiée du dimanche)

1. `git checkout -b drafts/AAAA-MM-JJ` (date du jour).
2. **Stratège** (toi) : lis les fichiers ci-dessus. Recherche l'actualité tech
   des 7 derniers jours (WebSearch, mode standard ; plusieurs requêtes : IA,
   Apple, Google, Microsoft, dev/open source, cybersécurité, matériel). Choisis un
   sujet par créneau de `config.json` pour la semaine qui vient (lundi à dimanche) :
   au plus 2 sujets d'actu et au moins 3 sujets durables (astuce, outil, explication).
   Écris le plan dans `content/plans/AAAA-Www.md` : sujet, format, angle, pourquoi.
3. **Créateur** (toi) : pour chaque créneau, crée `content/queue/<date>-<slug>/post.json`
   selon `content/SCHEMA.md`.
   - Accroche : 5 options basées sur `ig-reel/hooks.json`, notées avec
     `python3 .claude/skills/ig-reel/hookscore.py hooks.txt` ; garde la meilleure ≥ seuil.
   - Reel : 5 à 9 beats, 20 à 40 secondes, dernier beat qui reboucle sur l'accroche.
     Les reels sont **sans visage** : texte à l'écran + voix de synthèse. Choisis
     des sujets qui passent dans ce format (commande, chiffre, comparaison, étapes).
   - Carrousel : 6 à 9 slides, cover ≤ 8 mots, une idée par slide.
   - Légende : passe-la dans `python3 .claude/skills/ig-caption/caption.py`, puis
     `humanize.py` ; 3 à 5 hashtags précis, en fin de légende ; une seule demande d'action.
   - `verification.verdict` = `"pending"`.
4. **Vérificateur** : pour **chaque** post, lance un agent séparé (outil Agent,
   type general-purpose) avec comme consigne le contenu de
   `.claude/agents/verifier.md` suivi du chemin du post. Il ne doit pas voir ton
   raisonnement, seulement le fichier. Il écrit le verdict dans `post.json`.
   - `fail` : corrige les points signalés une fois, puis relance un vérificateur neuf.
   - Deuxième `fail` : supprime le post et note-le dans le plan.
5. `python3 pipeline/validate.py` doit sortir sans ERREUR. Corrige jusqu'à ce que ce soit le cas.
6. `git add -A && git commit -m "lot AAAA-Www" && git push -u origin HEAD`.
   GitHub Actions rend les médias et ouvre la PR tout seul.
7. Termine par un résumé de 5 lignes : sujets, formats, posts écartés et pourquoi.

## Procédure actu du mercredi

Cherche une actualité tech **majeure** depuis dimanche (sortie produit importante,
faille critique, annonce qui change l'usage). S'il n'y en a pas, ne fais rien et
dis-le. S'il y en a une : branche `drafts/AAAA-MM-JJ-actu`, un seul post pour le
prochain créneau carrousel libre (ou qui remplace celui de jeudi/samedi en
déplaçant l'ancien dossier vers `content/backlog/`), même procédure étapes 3 à 7.
