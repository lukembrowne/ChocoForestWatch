# Build stage
FROM node:18-alpine as build-stage

# Define build arguments
ARG VITE_API_URL
ARG VUE_APP_PLANET_API_KEY
ENV VITE_API_URL=$VITE_API_URL
ENV VUE_APP_PLANET_API_KEY=$VUE_APP_PLANET_API_KEY

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install -g @quasar/cli
RUN npm install

# Copy project files and build
COPY . .
RUN echo "VITE_API_URL=${VITE_API_URL}\nVUE_APP_PLANET_API_KEY=${VUE_APP_PLANET_API_KEY}" > .env.production
RUN quasar build

# Production stage
FROM nginx:alpine
COPY --from=build-stage /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 9000
CMD ["nginx", "-g", "daemon off;"]