FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["node", "-e", "const http=require('http');const fs=require('fs');const path=require('path');const mime={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.ico':'image/x-icon','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2'};const s=http.createServer((q,r)=>{let p=path.join('/app/dist',q.url==='/'?'index.html':q.url.split('?')[0]);if(!fs.existsSync(p)||!fs.statSync(p).isFile())p='/app/dist/index.html';r.setHeader('Content-Type',mime[path.extname(p)]||'application/octet-stream');r.end(fs.readFileSync(p));});s.listen(process.env.PORT||3000);"]
