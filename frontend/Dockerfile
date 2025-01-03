# Build stage
FROM node:18-alpine as build-stage

# Define build arguments
ARG VITE_API_URL
ARG VUE_APP_PLANET_API_KEY
ARG DJANGO_DEBUG
ENV VITE_API_URL=$VITE_API_URL
ENV VUE_APP_PLANET_API_KEY=$VUE_APP_PLANET_API_KEY
ENV DJANGO_DEBUG=$DJANGO_DEBUG

# # Validate DJANGO_DEBUG value
# RUN if [ "$DJANGO_DEBUG" != "True" ] && [ "$DJANGO_DEBUG" != "False" ]; then \
#     echo "Error: DJANGO_DEBUG must be either 'True' or 'False'" && \
#     echo "DJANGO_DEBUG: $DJANGO_DEBUG" && \
#     echo "VITE_API_URL: $VITE_API_URL" && \
#     echo "VUE_APP_PLANET_API_KEY: $VUE_APP_PLANET_API_KEY" && \
#     exit 1; \
#     fi

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install -g @quasar/cli
RUN npm install

# Copy project files
COPY . .

# If not in debug mode, build for production
RUN if [ "$DJANGO_DEBUG" != "True" ]; then \
    echo "Building for production..." && \
    echo "DJANGO_DEBUG: $DJANGO_DEBUG" && \
    echo "VITE_API_URL: $VITE_API_URL" && \
    echo "VUE_APP_PLANET_API_KEY: $VUE_APP_PLANET_API_KEY" && \
    echo "VITE_API_URL=${VITE_API_URL}\nVUE_APP_PLANET_API_KEY=${VUE_APP_PLANET_API_KEY}" > .env.production && \
    quasar build; \
    fi

# Development stage
FROM build-stage AS development
EXPOSE 9000
CMD ["npx", "quasar", "dev", "--hostname", "0.0.0.0"]

# Production stage
FROM nginx:alpine AS production
COPY --from=build-stage /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 9000
CMD ["nginx", "-g", "daemon off;"]

# No final stage selection here; use build targets instead