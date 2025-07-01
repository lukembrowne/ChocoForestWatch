# Build stage
FROM node:18-alpine as build-stage

# Define build arguments 
ARG VITE_API_URL
ARG DJANGO_DEBUG
ARG VITE_TITILER_URL
ARG VITE_DEFAULT_PUBLIC_PROJECT_ID
ARG VITE_UMAMI_WEBSITE_ID
ARG VITE_UMAMI_URL  

# Set environment variables
ENV VITE_API_URL=$VITE_API_URL
ENV DJANGO_DEBUG=$DJANGO_DEBUG
ENV VITE_TITILER_URL=$VITE_TITILER_URL
ENV VITE_DEFAULT_PUBLIC_PROJECT_ID=$VITE_DEFAULT_PUBLIC_PROJECT_ID
ENV VITE_UMAMI_WEBSITE_ID=${VITE_UMAMI_WEBSITE_ID}
ENV VITE_UMAMI_URL=${VITE_UMAMI_URL}

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
RUN npm config set registry https://registry.npmjs.org/
RUN npm install -g @quasar/cli --verbose
RUN npm install

# Copy project files
COPY . .

# If not in debug mode, build for production
RUN if [ "$DJANGO_DEBUG" != "True" ]; then \
    echo "Building for production..." && \
    echo "DJANGO_DEBUG: $DJANGO_DEBUG" && \
    echo "VITE_API_URL: $VITE_API_URL" && \
    echo "VITE_API_URL=${VITE_API_URL}" && \
    echo "VITE_TITILER_URL=${VITE_TITILER_URL}" && \
    echo "VITE_DEFAULT_PUBLIC_PROJECT_ID=${VITE_DEFAULT_PUBLIC_PROJECT_ID}" && \
    echo "VITE_UMAMI_WEBSITE_ID=${VITE_UMAMI_WEBSITE_ID}" && \
    echo "VITE_UMAMI_URL=${VITE_UMAMI_URL}" >> .env.production && \
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