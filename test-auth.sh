#!/bin/bash
export OPENOBSERVE_ADMIN_ACCOUNT="$(pass show OPENOBSERVE_ADMIN_ACCOUNT | tr -d '\n')"
export OPENOBSERVE_ROOT_PASSWORD="$(pass show OPENOBSERVE_ROOT_PASSWORD | tr -d '\n')"
export OPENOBSERVE_AUTH_HEADER="Basic $(echo -n "${OPENOBSERVE_ADMIN_ACCOUNT}:${OPENOBSERVE_ROOT_PASSWORD}" | base64 | tr -d '\n')"
echo $OPENOBSERVE_AUTH_HEADER
docker-compose config | grep AUTH
