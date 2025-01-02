FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./

# Install global dependencies
RUN npm install -g @quasar/cli

RUN npm install

# Copy project files
COPY . .

# Build the app
RUN quasar build

# Install serve to run the built app
RUN npm install -g serve

EXPOSE 9000

# Start Quasar in development mode
CMD [ "npx", "quasar", "dev", "--hostname", "0.0.0.0" ]

FROM nginx:alpine
COPY --from=0 /app/dist/spa /usr/share/nginx/html
EXPOSE 9000
CMD ["nginx", "-g", "daemon off;"]