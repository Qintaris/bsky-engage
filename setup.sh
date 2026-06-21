#!/usr/bin/env bash
set -e

echo "🦋 Bluesky Engage — Setup"
echo "========================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install it first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo ""
    echo "✏️  Edit .env with your Bluesky credentials:"
    echo "   nano .env"
    echo ""
    echo "   Need a Bluesky app password?"
    echo "   1. Go to https://bsky.app/settings"
    echo "   2. Click 'App Passwords'"
    echo "   3. Create one (name it 'bsky-engage')"
    echo ""
else
    echo "✅ .env already exists"
fi

# Test the script
echo ""
echo "🔍 Testing bsky_engage.py..."
python3 bsky_engage.py --dry-run --mode post --message "Test" 2>&1

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Edit .env with your credentials"
echo "   2. Post your first message:"
echo "      echo 'Hello Bluesky!' | python3 bsky_engage.py"
echo "   3. Or engage with your timeline:"
echo "      python3 bsky_engage.py --mode engage"
