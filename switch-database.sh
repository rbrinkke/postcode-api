#!/bin/bash
# Quick switcher between sample and production database

echo "Database Switcher"
echo "═════════════════"
echo ""
echo "Current configuration:"
if [ -f .env ]; then
    echo "  ✓ .env file exists"
    DB_PATH=$(grep "^DB_PATH=" .env | cut -d'=' -f2)
    if [[ "$DB_PATH" == *"sample"* ]]; then
        echo "  → Using: SAMPLE database"
    else
        echo "  → Using: PRODUCTION database"
    fi
else
    echo "  ℹ No .env file (using default: production)"
fi
echo ""

echo "Select database:"
echo "  1) Sample database (16 MB - development)"
echo "  2) Production database (11 GB - full data)"
echo "  3) Show current .env"
echo "  4) Exit"
echo ""
read -p "Choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "Switching to SAMPLE database..."
        cp .env.sample .env
        echo "✓ Done! .env now points to bag-sample.sqlite"
        echo ""
        echo "Run API with: ./run-with-env.sh"
        ;;
    2)
        echo ""
        echo "Switching to PRODUCTION database..."
        cp .env.production .env
        echo "✓ Done! .env now points to bag.sqlite"
        echo ""
        echo "Run API with: ./run-with-env.sh"
        ;;
    3)
        echo ""
        if [ -f .env ]; then
            echo "Current .env contents:"
            echo "─────────────────────"
            cat .env
        else
            echo "No .env file exists"
        fi
        ;;
    4)
        echo "Bye!"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
