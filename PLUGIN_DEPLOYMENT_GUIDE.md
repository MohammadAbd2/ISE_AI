# 🚀 Plugin Deployment Guide - HTML Fix

## Quick Summary
Fixed critical HTML rendering bug in JetBrains plugin that caused nested HTML tags in chat responses.

## What Changed
- **File:** `extensions/jetbrains/src/main/kotlin/com/ise/ai/copilot/ui/ChatPanel.kt`
- **Lines changed:** 75, 550, 567-568, 578
- **Type:** Bug fix (no new features)
- **Impact:** High (fixes display corruption)

## How to Deploy

### Option 1: From Built Artifact
1. Plugin JAR already built: `extensions/jetbrains/build/distributions/jetbrains-1.0.0.zip`
2. In JetBrains IDE: `Settings → Plugins → ⚙️ → Install Plugin from Disk`
3. Select the ZIP file and restart

### Option 2: Build Fresh
```bash
cd extensions/jetbrains
./gradlew build
# Built to: build/distributions/jetbrains-1.0.0.zip
```

## Verification Checklist
- [ ] Plugin loads without errors
- [ ] Simple text queries display cleanly (no nested HTML)
- [ ] Web search results display with proper formatting
- [ ] Streaming responses appear progressively without lag
- [ ] No console errors in IDE

## Test Scenarios

### Test 1: Simple Query
```
Input: "Hi, how are you today?"
Expected: Clean text response, no HTML tags visible
```

### Test 2: Search Query  
```
Input: "How many files are there in tests folder?"
Expected: Search results with sources, properly formatted
```

### Test 3: Long Response
```
Input: Ask for code generation or explanation
Expected: Smooth streaming without HTML corruption
```

## Troubleshooting

**Issue:** Plugin doesn't load
- ✓ Check JetBrains IDE version compatibility
- ✓ Clear plugin cache: `rm -rf ~/.config/JetBrains/*/plugins/ISEAICopilot`

**Issue:** Old version still showing
- ✓ Completely uninstall old plugin first
- ✓ Restart IDE
- ✓ Install new version

**Issue:** HTML still showing corrupted
- ✓ Clear browser cache (frontend)
- ✓ Restart backend server
- ✓ Verify plugin version: `Help → About → Plugins`

## Rollback Plan
If needed, revert to previous version:
```bash
git revert HEAD
cd extensions/jetbrains && ./gradlew build
```

## Files in Distribution
- `jetbrains-1.0.0.zip` - Complete plugin package
- `lib/` - Dependencies
- `classes/` - Compiled Kotlin code
- `plugin.xml` - Plugin configuration

---
**Version:** 1.0.0 (with HTML fix)
**Built:** April 8, 2026
**Status:** Ready for deployment ✅
