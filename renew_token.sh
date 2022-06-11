curl -X "POST" "http://docker.localhost:8200/v1/auth/token/renew-self" \
     -H 'X-Vault-Token: <VAULT_S3_TOKEN>' \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{}'