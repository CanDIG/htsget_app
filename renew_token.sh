echo "renewing S3 token"
curl -X "POST" "$VAULT_URL/v1/auth/token/renew-self" \
     -H 'X-Vault-Token: <VAULT_S3_TOKEN>' \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{}'