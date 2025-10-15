# Demo Mode

The Thematic Screener supports a **Demo Mode** that allows users to explore pre-computed examples without the ability to run custom analyses.

## Overview

When Demo Mode is enabled:
- ✅ **Quick Start Demos work**: Users can explore pre-computed analyses (Supply Chain, AI & Automation, Climate Tech)
- ✅ **All visualizations accessible**: Heatmaps, company cards, mindmaps, and evidence tables
- ✅ **Configuration panel viewable**: Users can see the configuration options
- ❌ **Run Analysis disabled**: The "Run Analysis" button is disabled with a message to contact support

## Use Cases

Demo Mode is perfect for:
- **Public demonstrations** - Show capabilities without API costs
- **Sales presentations** - Let prospects explore without credentials
- **Limited access deployments** - Share insights without allowing new analyses
- **Training environments** - Teach users the interface with safe, pre-loaded data

## Configuration

### Enable Demo Mode

Set the `DEMO_MODE` environment variable:

```bash
export DEMO_MODE=true
```

Or in your `.env` file:
```
DEMO_MODE=true
```

### Disable Demo Mode (Default)

Demo Mode is **disabled by default**. To explicitly disable it:

```bash
export DEMO_MODE=false
```

Or simply don't set the variable at all.

## User Experience

### When Demo Mode is Enabled

1. **Empty State**: The "Custom Configuration" button changes to "View Configuration"
2. **Configuration Panel**: 
   - Form fields are still visible (users can see what parameters exist)
   - The "Run Analysis" button is replaced with a disabled button showing a lock icon
   - Message displayed: *"Demo mode activated. For access to the full version, please contact support@bigdata.com or deploy your own version from GitHub."*
3. **Quick Start Demos**: Work normally, loading pre-computed JSON files

### When Demo Mode is Disabled

- Full functionality available
- "Run Analysis" button is enabled
- Users can submit custom analyses

## Technical Details

### Files Modified

1. **`settings.py`**: Added `DEMO_MODE: bool = False` setting
2. **`api/app.py`**: Passes `demo_mode` to the template
3. **`templates/api/index.html.jinja`**: Conditional button rendering based on `demo_mode`

### Button States

**Demo Mode OFF** (Default):
```html
<button type="submit" class="...bg-blue-600...">
  Run Analysis
</button>
```

**Demo Mode ON**:
```html
<button type="button" disabled class="...bg-zinc-700...opacity-50...">
  🔒 Run Analysis (Disabled)
</button>
<p class="text-amber-400">
  Demo mode activated. For access to the full version, please contact 
  support@bigdata.com or deploy your own version from GitHub.
</p>
```

## Testing Demo Mode

### Quick Test

1. Set the environment variable:
   ```bash
   export DEMO_MODE=true
   ```

2. Restart the service:
   ```bash
   python -m bigdata_thematic_screener
   ```

3. Open the web interface and verify:
   - ✅ Quick start demos load correctly
   - ✅ "Run Analysis" button is disabled and grayed out
   - ✅ Support contact message is displayed with both email and GitHub links
   - ✅ GitHub link opens in new tab to the repository
   - ✅ Configuration panel shows "View Configuration"

### Integration with Docker

Add to your Dockerfile or docker-compose.yml:

```yaml
environment:
  - DEMO_MODE=true
```

Or pass at runtime:
```bash
docker run -e DEMO_MODE=true bigdata-thematic-screener
```

## Support Contact

The demo mode message provides two options for users:

1. **Contact support**: [support@bigdata.com](mailto:support@bigdata.com)
2. **Deploy from GitHub**: [https://github.com/Bigdata-com/bigdata-thematic-screener](https://github.com/Bigdata-com/bigdata-thematic-screener)

This gives users the flexibility to either request enterprise access or deploy their own instance using the open-source repository.

To customize these links, modify the template in `index.html.jinja` around line 365.

## Reverting to Full Mode

To switch back to full functionality:

1. Unset or set to false:
   ```bash
   export DEMO_MODE=false
   ```
   
2. Restart the service

3. Verify "Run Analysis" button is now enabled and functional

## Security Note

Demo mode is a **frontend-only restriction**. If you need to completely disable the API endpoint for new analyses, consider:

1. Using authentication (set `ACCESS_TOKEN`)
2. Implementing IP allowlisting
3. Deploying separate instances for demo vs. production

The current implementation disables the UI but does not block direct API calls to `/thematic-screener`.

