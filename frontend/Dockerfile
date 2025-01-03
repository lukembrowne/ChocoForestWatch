# Build stage
FROM node:18-alpine as build-stage

# Define build arguments
ARG VITE_API_URL
ARG VUE_APP_PLANET_API_KEY
ARG DJANGO_DEBUG
ENV VITE_API_URL=$VITE_API_URL
ENV VUE_APP_PLANET_API_KEY=$VUE_APP_PLANET_API_KEY
ENV DJANGO_DEBUG=$DJANGO_DEBUG

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
    echo "VITE_API_URL=${VITE_API_URL}\nVUE_APP_PLANET_API_KEY=${VUE_APP_PLANET_API_KEY}" > .env.production && \
    quasar build; \
    fi

# Choose final image based on DJANGO_DEBUG
FROM nginx:alpine as production
COPY --from=build-stage /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 9000
CMD ["nginx", "-g", "daemon off;"]

FROM build-stage as development
EXPOSE 9000
CMD ["npx", "quasar", "dev", "--hostname", "0.0.0.0"]

# Select the appropriate final stage
FROM ${DJANGO_DEBUG:+development}${DJANGO_DEBUG:-production} as final