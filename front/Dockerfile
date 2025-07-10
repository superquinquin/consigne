FROM node:lts-alpine

RUN npm install -g http-server

WORKDIR /app


COPY ./front/package*.json ./

# RUN npm install tailwindcss @tailwindcss/cli @tailwindcss/postcss postcss
RUN npm install

COPY ./front .

RUN npm run build

EXPOSE 8123