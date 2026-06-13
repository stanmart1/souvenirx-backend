# Frontend Restart Issue - Root Cause & Fix

## Problem
The frontend container kept restarting on Coolify deployment.

## Root Cause Analysis

### Issue #1: Missing HTTP Server
The TanStack Start build output (`dist/server/server.js`) is **NOT an executable Node.js HTTP server**. It's a module that exports a fetch handler designed for edge runtimes (Cloudflare Workers, etc.).

**What was wrong:**
```dockerfile
CMD ["node", "dist/server/server.js"]  # This doesn't start an HTTP server!
```

The `dist/server/server.js` file exports:
```javascript
export default {
  async fetch(request, env, ctx) {
    // ... handles requests
  }
}
```

This is a **fetch handler**, not an HTTP server. Running it directly with `node` does nothing - the process starts and immediately exits, causing Coolify to restart it repeatedly.

### Issue #2: Missing HOSTNAME Binding
Even if we had a proper HTTP server, it needs to bind to `0.0.0.0` (all interfaces) to be accessible from Coolify's health checks and reverse proxy. The default `127.0.0.1` only allows connections from within the container.

## Solution

### Created HTTP Server Wrapper (`server.mjs`)
A Node.js HTTP server that:
1. Creates an actual HTTP server using Node's `http` module
2. Converts incoming HTTP requests to `Request` objects
3. Calls the TanStack Start fetch handler
4. Converts the Response back to HTTP response
5. Binds to `0.0.0.0:3000` for external access
6. Handles graceful shutdown on SIGTERM/SIGINT

### Key Features:
- ✅ Proper HTTP server that stays running
- ✅ Binds to `0.0.0.0` for Coolify access
- ✅ Handles proxy headers (`x-forwarded-proto`, `x-forwarded-host`)
- ✅ Graceful shutdown support
- ✅ Error handling with fallback error page
- ✅ Works with TanStack Start's SSR

## Updated Configuration

### Dockerfile Changes:
```dockerfile
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0                    # Bind to all interfaces
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/server.mjs ./server.mjs  # HTTP server wrapper
EXPOSE 3000
CMD ["node", "server.mjs"]              # Run the HTTP server
```

### Files Modified:
1. **Dockerfile** - Updated to use `server.mjs` instead of `dist/server/server.js`
2. **server.mjs** - Created new HTTP server wrapper

### Files Created:
- `server.mjs` - Node.js HTTP server that wraps the TanStack Start fetch handler

## Why This Approach?

### Alternative Approaches Considered:

1. **Use nginx** - ❌ Not suitable for SSR applications (TanStack Start needs server-side rendering)

2. **Use static export** - ❌ Would require reconfiguring TanStack Start for SSG mode, losing SSR benefits

3. **Use a different server adapter** - ❌ TanStack Start's built-in adapters are for edge runtimes, not Node.js HTTP

4. **HTTP Server Wrapper** - ✅ **Best solution** - Works with existing build output, maintains SSR, simple to understand

## Testing

### Local Test:
```bash
cd souvenirx-frontend
npm run build
PORT=3001 node server.mjs
curl http://localhost:3001/  # Should return 200
```

### Docker Test:
```bash
docker build -t souvenirx-frontend .
docker run -p 3000:3000 -e VITE_API_URL=https://api.souvenir-x.com souvenirx-frontend
curl http://localhost:3000/  # Should return 200
```

## Deployment Checklist

- [x] HTTP server wrapper created (`server.mjs`)
- [x] Dockerfile updated to use `server.mjs`
- [x] Environment variable `HOSTNAME=0.0.0.0` set
- [x] Port 3000 exposed
- [x] Build tested locally
- [x] Server tested locally
- [x] Ready for Coolify deployment

## Environment Variables (Coolify)

Required:
```
VITE_API_URL=https://api.souvenir-x.com
VITE_WHATSAPP_NUMBER=2348000000000
```

Optional:
```
PORT=3000           # Default: 3000
HOSTNAME=0.0.0.0    # Default: 0.0.0.0
NODE_ENV=production # Set automatically in Dockerfile
```

## Expected Behavior After Deploy

1. Container starts successfully
2. HTTP server listens on `0.0.0.0:3000`
3. Coolify health checks pass
4. Container stays running (no restarts)
5. SSR works correctly
6. API calls to Python backend work

## Monitoring

After deployment, check:
1. Container status in Coolify (should be "Running")
2. Logs should show: `Server running at http://0.0.0.0:3000/`
3. No restart loops
4. Website loads correctly
5. SSR is working (view page source, should see rendered HTML)

## Summary

**Before:** `dist/server/server.js` is a fetch handler, not an HTTP server → container exits → Coolify restarts

**After:** `server.mjs` is a proper HTTP server → wraps fetch handler → stays running → Coolify happy

The frontend should now deploy successfully without restart issues! 🚀
