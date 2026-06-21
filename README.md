# Bluesky Engage 🦋

Engagement authentique sur Bluesky — zéro dépendance, stdlib Python uniquement.

Postez, likez, followez et commentez depuis votre terminal. Pas de template, pas de pool de messages pré-écrits, pas de comportement de bot.

## ✨ Fonctionnalités

- **Post** — Publier un message sur votre timeline
- **Engage** — Follow, like et commentez les posts de votre fil
- **Photo** — Poster une image avec description
- **Comment** — Commenter les posts récents de votre timeline
- **Dry-run** — Simuler sans rien publier

## 🚀 Installation

```bash
git clone https://github.com/Qintaris/bsky-engage.git
cd bsky-engage
```

Zéro dépendance externe — seulement la stdlib Python 3.

## ⚙️ Configuration

Copier le fichier d'exemple et le remplir :

```bash
cp .env.example .env
# Editer .env avec vos identifiants
```

Ou exporter les variables d'environnement :

```bash
export BSKY_HANDLE="votre-handle.bsky.social"
export BSKY_PASSWORD="votre-mot-de-passe-app"
```

### Obtenir un mot de passe d'application

1. Allez dans **Settings > App Passwords** sur bsky.app
2. Créez un nouveau mot de passe d'application
3. Utilisez-le comme `BSKY_PASSWORD`

> ⚠️ **Ne jamais commit votre `.env` ou exposer votre mot de passe.**

## 📖 Usage

```bash
# Poster un message
echo "Mon premier post avec bsky-engage ! #python" | python3 bsky_engage.py --mode post

# Engagement social (follow + like + comment)
python3 bsky_engage.py --mode engage

# Poster ET engager
python3 bsky_engage.py --mode all

# Poster une image
python3 bsky_engage.py --mode photo --message "Ma photo du jour" --image ~/photo.jpg

# Simuler sans rien faire
python3 bsky_engage.py --dry-run

# Message personnalisé
python3 bsky_engage.py --mode post --message "Un post écrit à la main 🎯"

# Contrôler le volume d'engagement
python3 bsky_engage.py --mode engage --max-follows 3 --max-likes 5 --max-comments 2
```

## 🎯 Modes

| Mode | Action | Usage |
|------|--------|-------|
| `post` | Publie un message | Post uniquement |
| `engage` | Follow 5 comptes, like 3 posts, 1 commentaire | Engagement social |
| `all` | Post + engage | Les deux |
| `comment` | Commente jusqu'à N posts | Interaction ciblée |
| `photo` | Poste une image + texte | Posts visuels |

## 🏗️ Architecture

- **Zéro dépendance** — `urllib` standard uniquement
- **AT Protocol natif** — Appels directs à l'API Bluesky (pas de SDK)
- **Tout en environnements** — Pas de secrets dans le code
- **Portable** — Marche sur Python 3.8+, Linux/macOS/Windows

## 🤝 Contribution

Les PRs sont les bienvenues ! Idées d'amélioration :

- Mode `--schedule` pour planifier des posts
- Support des threads
- Statistiques d'engagement
- Analyse des meilleurs horaires de publication

## 📄 Licence

MIT — fait avec ❤️ par [Aria Dubois](https://github.com/Qintaris)
