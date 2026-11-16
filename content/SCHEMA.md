# Format d'un post

Chaque post est un dossier `content/queue/AAAA-MM-JJ-slug/` qui contient un
`post.json`. Les médias (`slides/*.jpg`, `reel.mp4`, `cover.jpg`) sont générés
par GitHub Actions : ne les écris jamais à la main.

```json
{
  "id": "2026-11-23-mac-reglages-caches",
  "type": "carousel",                       // "carousel" | "reel"
  "publish_at": "2026-11-23T18:40:00-05:00",
  "topic": "3 réglages macOS qui ralentissent ton Mac",
  "angle": "pourquoi ça compte pour le public cible, en une phrase",
  "hook": "Ton Mac ralentit à cause de 3 réglages cachés.",
  "hook_formula": "#7 Hidden Cost",          // id tiré de .claude/skills/ig-reel/hooks.json
  "sources": [
    {"title": "Apple Support – ...", "url": "https://support.apple.com/..."}
  ],

  "carousel": {                              // seulement si type = carousel
    "slides": [
      {"kind": "cover", "title": "Ton Mac ralentit à cause de **3 réglages**", "subtitle": "Le 2e est activé par défaut"},
      {"kind": "text",  "title": "Pourquoi", "body": "Une phrase. Deux au maximum."},
      {"kind": "list",  "title": "Les 3 réglages", "items": ["Un", "Deux", "Trois"]},
      {"kind": "code",  "title": "La commande", "code": "defaults write ...", "lang": "bash"},
      {"kind": "stat",  "value": "-38 %", "label": "de RAM utilisée après le changement", "note": "Source : ..."},
      {"kind": "cta",   "title": "Enregistre-le", "body": "Pour la prochaine fois que ton Mac rame."}
    ]
  },

  "reel": {                                  // seulement si type = reel
    "cover_title": "3 réglages cachés",
    "beats": [
      {"role": "hook", "voice": "Phrase dite à voix haute.", "screen": "Texte court à l'écran", "kind": "title"},
      {"role": "body", "voice": "...", "screen": "...", "kind": "text"},
      {"role": "body", "voice": "...", "screen": "brew install x", "kind": "code"},
      {"role": "body", "voice": "...", "screen": "-38 %", "kind": "stat", "label": "de RAM"},
      {"role": "cta",  "voice": "...", "screen": "...", "kind": "text"}
    ]
  },

  "caption": "Texte complet de la légende, hashtags compris (5 maximum), à la fin.",
  "verification": {
    "verdict": "pass",                       // "pass" | "fail" | "pending"
    "checked_at": "2026-11-22T15:02:00Z",
    "notes": ["Affirmation X vérifiée sur la source 1", "..."]
  }
}
```

Règles :
- `**mot**` dans un titre de slide ou dans `screen` = mot mis en couleur d'accent.
- Slide `kind` : `cover`, `text`, `list`, `code`, `stat`, `cta`. La 1re slide est toujours `cover`, la dernière toujours `cta`.
- Beat `kind` : `title`, `text`, `code`, `stat`. Le 1er beat a `role: hook`, le dernier `role: cta`.
- `screen` : 8 mots maximum. `voice` : une phrase, rarement deux.
- Tout chiffre, nom de produit, version ou date dans le post doit venir d'une des `sources`.
- `publish_at` doit correspondre à un créneau de `config.json`.
