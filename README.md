# Bluesky Engage 🦋

Engagement authentique sur Bluesky — zéro dépendance, stdlib Python uniquement.

```
echo "Hello Bluesky !" | python3 bsky_engage.py
```

## ✨ Clé en main — 30 secondes

```bash
# 1. Cloner
git clone https://github.com/Qintaris/bsky-engage.git
cd bsky-engage

# 2. Configurer
cp .env.example .env
nano .env   # Mets ton handle et ton mot de passe d'application

# 3. Poster ton premier message
echo "Mon premier post avec bsky-engage 🦋" | python3 bsky_engage.py --mode post

# 4. Engager (liker, follow, commenter)
python3 bsky_engage.py --mode engage

# 5. Poster + Engager en une commande
echo "Bonne journée à tous !" | python3 bsky_engage.py --mode all
```

## 🔧 Prérequis

- **Python 3.8+** (vérifie avec `python3 --version`)
- **Un compte Bluesky** + un mot de passe d'application

### Obtenir un mot de passe d'application

1. Va sur **bsky.app** → **Settings** → **App Passwords**
2. Crée un nouveau mot de passe (ex: "bsky-engage")
3. Copie-le dans `.env` comme `BSKY_PASSWORD`

> ⚠️ **Ne partage jamais ton .env** — il contient ton mot de passe.

## 📖 Usage complet

```bash
# Poster un message (stdin)
echo "Je découvre Bluesky ! #debutant" | python3 bsky_engage.py --mode post

# Poster avec --message
python3 bsky_engage.py --mode post --message "Post écrit directement en CLI"

# Engagement social (follow 5 comptes, 3 likes, 1 commentaire)
python3 bsky_engage.py --mode engage

# Poster + engager (le combo du quotidien)
echo "Belle journée ensoleillée 🌞" | python3 bsky_engage.py --mode all

# Poster une photo
python3 bsky_engage.py --mode photo --message "Ma photo du jour" --image ~/photo.jpg

# Simuler pour voir ce qui va se passer
python3 bsky_engage.py --dry-run

# Contrôler le volume
python3 bsky_engage.py --mode engage --max-follows 2 --max-likes 5 --max-comments 2

# Trouver ton meilleur horaire de publication
python3 bsky_engage.py --best-time
```

## 🎯 Les 5 modes

| Mode | Usage | À quoi ça sert |
|------|-------|----------------|
| `post` | Poster un message | Publier sur ton fil |
| `engage` | Like + follow + comment | Interagir avec ta communauté |
| `all` | Les deux | Routine quotidienne complète |
| `comment` | Commente uniquement | Engagement ciblé |
| `photo` | Image + texte | Posts visuels |

## ❓ Aide rapide

```bash
# Voir toutes les options
python3 bsky_engage.py --help

# Vérifier que tout est OK sans rien faire
python3 bsky_engage.py --dry-run

# Voir les logs
tail -f bsky_engage.log
```

## 🏗️ Pas de dépendances

Le script utilise uniquement la **stdlib Python** (urllib, json, os, sys). 
Pas de pip install, pas de requirements.txt, pas de node_modules.

```
# Ça marche directement :
python3 bsky_engage.py --dry-run
```

## 🧪 Features avancées (déjà incluses)

| Feature | Pourquoi | Usage |
|---------|----------|-------|
| 🧵 **Thread** | Répondre à ton dernier post | `--thread` |
| 🔗 **Reply** | Répondre à un post spécifique | `--reply-to at://...` |
| 📊 **Stats** | Récap de session | `--stats` (actif par défaut) |
| ⏰ **Schedule** | Planifier un post | `--in "30min"` ou `--at "14:00"` |
| 🏆 **Best Time** | Trouver le meilleur moment pour poster | `--best-time --best-time-posts 50` |

## 🤝 Contribuer

PRs bienvenues ! Ce qui n'existe PAS encore :
- Threads longs automatiques (N replies à la suite)
- Stats historiques (engagement par post, tendances)
- Mode `--cron` pour scheduler sans `at`

## 💛 Soutenir

Si `bsky-engage` te fait gagner du temps, tu peux soutenir le projet :

[Faire un don via PayPal](https://www.paypal.com/donate/?hosted_button_id=95T36AZHYRJ82)

## 📄 Licence

MIT — par [Aria Dubois](https://github.com/Qintaris)
