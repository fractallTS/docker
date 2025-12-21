FROM nginx:latest
WORKDIR /html
COPY nginx.conf /etc/nginx/sites-available/default
COPY index.html /usr/share/nginx/html/index.html
RUN apt-get update && apt-get install -y certbot python3-certbot-nginx
# RUN certbot certonly --test-cert --nginx --non-interactive --agree-tos --register-unsafely-without-email -d "$DOMAIN" --preferred-challenges http --redirect
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]