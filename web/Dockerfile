# Этап 1: сборка React
FROM node:20.20.2-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
RUN npm run build

# Этап 2: Apache раздаёт сборку и проксирует /api
FROM httpd:2.4.69
COPY httpd.conf /usr/local/apache2/conf/httpd.conf
COPY --from=build /app/dist /usr/local/apache2/htdocs/