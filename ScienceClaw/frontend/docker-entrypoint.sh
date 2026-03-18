#!/bin/sh

# Replace environment variables in nginx config
envsubst '${BACKEND_URL} ${TASK_SERVICE_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start nginx
nginx -g "daemon off;" 