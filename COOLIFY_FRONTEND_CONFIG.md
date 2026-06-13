# Coolify Frontend Configuration - Verification

## ✅ Dockerfile Configuration

### Current Dockerfile Status:
```dockerfile
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
COPY --from=builder /app/dist ./dist
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" || exit 1
CMD ["node", "dist/server/server.js"]
```

### ✅ Coolify Requirements Met:

1. **Multi-stage build** - Optimized for smaller final image
2. **Deterministic dependencies** - Uses `npm ci` with `package-lock.json`
3. **Production environment** - Sets `NODE_ENV=production`
4. **Port exposure** - Exposes port 3000 (Coolify default)
5. **Host binding** - Sets `HOSTNAME=0.0.0.0` for Coolify networking
6. **Health check** - Added HTTP health check for Coolify monitoring
7. **Correct entry point** - Uses `dist/server/server.js` (TanStack Start output)

## ✅ Environment Variables

### Required in Coolify:
```
VITE_API_URL=https://api.yourdomain.com
VITE_WHATSAPP_NUMBER=2348000000000
```

### Notes:
- Variables with `VITE_` prefix are automatically available in the frontend
- `VITE_API_URL` should point to your backend API domain
- `VITE_WHATSAPP_NUMBER` is for the WhatsApp chat button

## ✅ .dockerignore Configuration

### Current exclusions:
- ✅ `.git`, `.gitignore` - Version control
- ✅ `.env`, `.env.*` - Environment files (use Coolify env vars instead)
- ✅ `node_modules` - Dependencies (rebuild in container)
- ✅ `dist` - Build output (rebuild in container)
- ✅ `.vscode`, `.idea` - IDE files
- ✅ `.DS_Store`, `Thumbs.db` - OS files
- ✅ `Dockerfile`, `docker-compose*.yml` - Docker files
- ✅ `*.md`, `LICENSE` - Documentation
- ✅ `.wrangler` - Cloudflare files

### Important: `.tanstack` is NOT ignored
- TanStack Start uses `.tanstack/` for build artifacts
- The build process needs this directory
- It was previously ignored but is now included

## ✅ Build Output Verification

### TanStack Start Build Output:
```
dist/
├── client/
│   └── assets/     # Static assets (CSS, JS, images)
└── server/
    ├── assets/     # Server-side assets
    └── server.js   # Entry point (SSR server)
```

### Dockerfile matches this structure:
- Copies `/app/dist` to `/app/dist` in runner
- Runs `node dist/server/server.js`
- Exposes port 3000

## ✅ Coolify Service Configuration

### Recommended Coolify Settings:

**Service Type:** Dockerfile

**Build Context:** `./souvenirx-frontend`

**Dockerfile:** `Dockerfile`

**Port:** 3000

**Environment Variables:**
- `VITE_API_URL` - Your backend API URL
- `VITE_WHATSAPP_NUMBER` - WhatsApp contact number

**Health Check:** Built-in (Dockerfile includes HTTP check)

**Domain:** Configure your frontend domain in Coolify

**SSL:** Enable Let's Encrypt in Coolify

## ✅ Network Configuration

### Current Setup:
- Exposes port 3000
- Binds to `0.0.0.0` (all interfaces)
- Compatible with Coolify's reverse proxy
- Works with Coolify's networking layer

## ✅ Health Check

### Dockerfile Health Check:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" || exit 1
```

### Behavior:
- Checks every 30 seconds
- Times out after 10 seconds
- Waits 40 seconds before first check (allows startup)
- Retries 3 times before marking unhealthy
- Coolify will restart container if unhealthy

## ✅ Resource Recommendations

Based on TanStack Start + React 19 + Vite:

**CPU:** 0.5-1 core
**Memory:** 256MB-1GB
**Disk:** 1GB (static assets are small)

## ✅ Deployment Checklist

- [x] Dockerfile uses multi-stage build
- [x] `package-lock.json` exists for reproducible builds
- [x] Build output directory matches Dockerfile (`dist/`)
- [x] Entry point is correct (`dist/server/server.js`)
- [x] Port 3000 exposed
- [x] Host binding to `0.0.0.0`
- [x] Health check configured
- [x] `.dockerignore` excludes unnecessary files
- [x] `.tanstack` NOT ignored (needed for build)
- [x] Environment variables documented
- [x] Compatible with Coolify networking

## Summary

The frontend Dockerfile is **fully configured for Coolify deployment**:

✅ Multi-stage build for optimization
✅ Deterministic dependency installation
✅ Correct build output paths
✅ Health check for monitoring
✅ Proper port and host configuration
✅ Environment variable support
✅ Optimized `.dockerignore`

**Ready for Coolify deployment!** 🚀
