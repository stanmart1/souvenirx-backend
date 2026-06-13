# Hero Image Loading Fix

## Problem
The hero section image on the homepage was not loading. There should have been a fallback to a hardcoded image (`src/assets/hero.jpg`) until the admin uploads a custom image.

## Root Cause
**Variable name shadowing** - The imported hero image was being overwritten:

```typescript
// Line 4: Import hero image
import hero from "@/assets/hero.jpg";

// Line 73: This overwrites the imported 'hero' variable!
const hero = homepageContent?.hero || { ... };

// Line 213: This tries to use 'hero' as an image src
<img src={hero} alt="..." />  // 'hero' is now an object, not an image!
```

The `hero` content object from the API was replacing the imported image, causing the `<img src={hero}>` to render as `<img src="[object Object]">` which failed to load.

## Solution

### 1. Renamed the imported image
```typescript
// Before
import hero from "@/assets/hero.jpg";

// After
import defaultHeroImage from "@/assets/hero.jpg";
```

### 2. Renamed the content object
```typescript
// Before
const hero = homepageContent?.hero || { ... };

// After
const heroContent = homepageContent?.hero || { 
  // ... content
  image: null,  // Add image field
};
```

### 3. Added fallback logic
```typescript
// Use admin-uploaded image or fallback to default
const heroImage = heroContent.image || defaultHeroImage;
```

### 4. Updated all references
```typescript
// Updated hero section rendering
{heroContent.badge.enabled && ...}
<h1>{heroContent.headline}</h1>
<p>{heroContent.subheadline}</p>
<Link to={heroContent.primary_cta.link}>...</Link>

// Updated image src
<img src={heroImage} alt="Custom souvenirs" />
```

## How It Works Now

### Scenario 1: No admin image uploaded (default)
```
heroContent.image = null
  ↓
heroImage = null || defaultHeroImage
  ↓
heroImage = "/assets/hero-BL2m3e_3.jpg" (bundled static asset)
  ↓
<img src="/assets/hero-BL2m3e_3.jpg" /> ✅
```

### Scenario 2: Admin uploads custom image
```
heroContent.image = "https://cdn.example.com/custom-hero.jpg"
  ↓
heroImage = "https://cdn.example.com/custom-hero.jpg" || defaultHeroImage
  ↓
heroImage = "https://cdn.example.com/custom-hero.jpg"
  ↓
<img src="https://cdn.example.com/custom-hero.jpg" /> ✅
```

## Build Output Verification

The static hero image is correctly bundled:
```
dist/client/assets/hero-BL2m3e_3.jpg    212.85 kB
```

## Server Verification

### Test 1: HTML rendering
```bash
curl http://localhost:3002/ | grep hero
# Output: src="/assets/hero-BL2m3e_3.jpg" ✅
```

### Test 2: Image serving
```bash
curl -I http://localhost:3002/assets/hero-BL2m3e_3.jpg
# Output:
# HTTP/1.1 200 OK
# Content-Type: image/jpeg
# Cache-Control: public, max-age=31536000, immutable ✅
```

## Files Modified
- `src/routes/index.tsx` - Fixed variable shadowing, added fallback logic

## Admin Dashboard Integration

When the admin uploads a hero image in the admin dashboard:
1. Admin uploads image via `/admin/homepage`
2. Image URL is stored in `homepage_content.hero.image`
3. Frontend fetches homepage content
4. `heroContent.image` contains the uploaded URL
5. `heroImage = heroContent.image` (uses admin image)
6. Homepage displays admin's custom hero image ✅

When no image is uploaded:
1. Admin hasn't uploaded image yet
2. `homepage_content.hero.image` is null/undefined
3. `heroImage = null || defaultHeroImage` (fallback)
4. Homepage displays the default hero image ✅

## Summary

**Before:** Variable shadowing caused hero image to be `[object Object]` → broken image

**After:** Proper variable naming + fallback logic → displays default image until admin uploads custom one

The homepage hero image now loads correctly with a working fallback mechanism! 🎨✨
