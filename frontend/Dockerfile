FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./

# Install global dependencies
RUN npm install -g @quasar/cli

RUN npm install

# Copy project files
COPY . .

# Build the app
RUN npm run build

# Install serve to run the built app
RUN npm install -g serve

EXPOSE 9000

# Start Quasar in development mode
CMD [ "npx", "quasar", "dev", "--hostname", "0.0.0.0" ]