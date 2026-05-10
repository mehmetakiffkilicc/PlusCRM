# Frontend Dockerfile - Multi-stage Build
# Stage 1: Build
FROM node:20-slim AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Accept VITE_API_URL as build argument for Railway deployment
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the app
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy build output to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Railway routing will map to exposed port automatically
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
