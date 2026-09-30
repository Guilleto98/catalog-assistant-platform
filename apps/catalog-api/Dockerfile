FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run db:generate && npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production DATABASE_URL=file:/app/prisma/data/dev.db PORT=3000
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/prisma ./prisma
COPY --from=build /app/data ./data
COPY --from=build /app/package.json ./package.json
EXPOSE 3000
CMD ["sh", "-c", "npx prisma migrate deploy && npm run db:seed && node dist/main.js"]
