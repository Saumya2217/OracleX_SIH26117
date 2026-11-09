ARG NGINX_BASE_IMAGE=nginx:1.29.6-alpine3.23@sha256:f46cb72c7df02710e693e863a983ac42f6a9579058a59a35f1ae36c9958e4ce0
FROM ${NGINX_BASE_IMAGE}

COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
