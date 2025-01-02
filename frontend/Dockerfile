# Build stage
FROM node:18-alpine as build-stage

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install -g @quasar/cli
RUN npm install

# Copy project files and build
COPY . .
RUN quasar build

# Production stage
FROM nginx:alpine
COPY --from=build-stage /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 9000
CMD ["nginx", "-g", "daemon off;"]