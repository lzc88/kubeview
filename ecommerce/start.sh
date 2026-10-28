#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

for env_file in orders/config/.env payments/config/.env; do
    if [[ ! -f "$env_file" ]]; then
        echo "missing $env_file: copy $env_file.example and fill it in" >&2
        exit 1
    fi
done

STRIPE_API_KEY="$(grep '^STRIPE_API_KEY=' payments/config/.env | cut -d= -f2- | tr -d '"\r')"
if [[ -z "$STRIPE_API_KEY" || "$STRIPE_API_KEY" == *change-me* ]]; then
    echo "set STRIPE_API_KEY in payments/config/.env" >&2
    exit 1
fi
export STRIPE_API_KEY

STRIPE_WEBHOOK_SECRET="$(docker run --rm -e STRIPE_API_KEY stripe/stripe-cli:v1.53.1 listen --print-secret)"
if [[ "$STRIPE_WEBHOOK_SECRET" != whsec_* ]]; then
    echo "could not get a webhook secret from the Stripe CLI: $STRIPE_WEBHOOK_SECRET" >&2
    exit 1
fi

current="$(grep '^STRIPE_WEBHOOK_SECRET=' payments/config/.env | cut -d= -f2- | tr -d '"\r' || true)"
if [[ "$current" != "$STRIPE_WEBHOOK_SECRET" ]]; then
    rest="$(grep -v '^STRIPE_WEBHOOK_SECRET=' payments/config/.env || true)"
    printf '%s\nSTRIPE_WEBHOOK_SECRET=%s\n' "$rest" "$STRIPE_WEBHOOK_SECRET" > payments/config/.env
    echo "updated STRIPE_WEBHOOK_SECRET in payments/config/.env"
fi

docker compose up --build "$@"
