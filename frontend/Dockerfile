# Use lightweight Nginx
FROM nginx:1.28-alpine

# Remove default Nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx config
COPY nginx/portfolio.conf /etc/nginx/conf.d/default.conf

# Copy frontend static files
COPY dist/ /usr/share/nginx/html/

# Expose HTTP port
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]