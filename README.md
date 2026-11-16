# Agent Instagram tech

Système qui alimente un compte Instagram tech francophone en reels (sans
visage) et en carrousels. Tu approuves les posts une fois par semaine, depuis
ton téléphone, et le système s'occupe du reste.

```
 Dimanche (Claude, tâche planifiée)        GitHub Actions                     Toi
 ─────────────────────────────────        ───────────────                    ───
 Stratège : stats + veille tech  ──┐
 Créateur : post.json par créneau  ├─push drafts/…─► rendu slides + reel ─► PR avec aperçus
 Vérificateur (agent séparé)     ──┘                                         │
                                                                     fusionner = approuver
                                            publication horaire ◄────────────┘
                                            (API Instagram officielle)
 Mercredi : actu majeure ? 1 post de plus     stats chaque dimanche
```

## Ce qui tourne où

| Partie | Où | Déclencheur |
|---|---|---|
| Stratégie, écriture, vérification | Tâche planifiée Claude | dimanche + mercredi |
| Rendu des carrousels (JPEG 1080×1350) | `drafts.yml` | push sur `drafts/**` |
| Rendu des reels (MP4 1080×1920, voix Piper) | `drafts.yml` | idem |
| Publication | `publish.yml` | toutes les heures, un post max |
| Statistiques | `insights.yml` | dimanche 8 h 23 (heure de l'Est) |
| Renouvellement du jeton | `refresh-token.yml` | le 1er et le 15 du mois |

## Garde-fous

- Rien ne part sans **PR fusionnée**. Si tu ne fais rien, rien n'est publié.
- `pipeline/validate.py` bloque : accroche sous 65/100, plus de 5 hashtags,
  vérification factuelle non passée, slides mal formées, reel de plus de 45 s.
- Le vérificateur est un agent séparé, qui ne voit que le fichier.
- Un post par heure au maximum.

## Secrets GitHub nécessaires

| Secret | Contenu |
|---|---|
| `IG_ACCESS_TOKEN` | jeton longue durée de l'API Instagram (Instagram Login) |
| `GH_PAT` *(facultatif)* | jeton GitHub à granularité fine, permission « Secrets : lecture et écriture » sur ce dépôt, pour renouveler `IG_ACCESS_TOKEN` automatiquement |

## Commandes utiles

```bash
python3 pipeline/validate.py                     # vérifier la file d'attente
python3 pipeline/build.py                        # rendre les médias en local
IG_ACCESS_TOKEN=... python3 pipeline/publish.py --check   # tester le jeton
```

Lancer la publication à la main : onglet **Actions → Publication → Run workflow**
(simulation par défaut).

## Crédits

Les skills `ig-*` viennent de
[Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)
(MIT, voir `.claude/skills/LICENSE-ig-skills-MIT`). Ils ont reçu une extension
française : lexique de l'humanizer, mots du noteur d'accroches, appels à
l'action de `caption.py`.
