FROM nginx:1.27-alpine

# Upstream API address; substituted into the nginx config at container start
ENV BACKEND_URL=http://backend:8000

# Files in /etc/nginx/templates/*.template are processed with envsubst by the nginx entrypoint
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY public/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1
