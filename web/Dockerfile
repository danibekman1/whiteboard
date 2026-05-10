FROM node:20-alpine AS deps
WORKDIR /app
RUN apk add --no-cache python3 make g++
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build
WORKDIR /app
RUN apk add --no-cache python3 make g++
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
RUN apk add --no-cache python3 make g++
# Install the claude CLI for the agent_sdk dev backend. Adds ~50 MB to
# the image; only used when CHAT_BACKEND=agent_sdk. Prod compose doesn't
# set that env var, so the binary sits idle.
# Note: claude CLI refuses --dangerously-skip-permissions under root, so the
# runtime stage drops to the `node` user (uid 1000, ships with node:alpine).
RUN npm install -g @anthropic-ai/claude-code
COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/package.json ./
COPY --from=build --chown=node:node /app/node_modules ./node_modules
USER node
EXPOSE 3000
CMD ["npm", "start"]
