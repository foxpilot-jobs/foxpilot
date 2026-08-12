FROM node:24.19.0-bookworm-slim AS build

WORKDIR /app

# Set NPM_STRICT_SSL=true in normal deployments with a trusted CA bundle.
ARG NPM_STRICT_SSL=false
COPY package.json package-lock.json .npmrc ./
RUN npm config set strict-ssl "${NPM_STRICT_SSL}" \
  && npm ci --include=optional --no-audit --no-fund --registry=https://registry.npmjs.org/
COPY . .
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
