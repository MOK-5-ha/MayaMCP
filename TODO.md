# TODOs

## Stripe Payment Integration Setup

The Stripe payment feature has been implemented with a mock/fallback mode that works out of the box. To enable real Stripe integration, follow these steps:

### Current Status

✅ **Works immediately without any setup:**
- Tab overlay displays on Maya's avatar
- Balance tracking ($1000 starting balance)
- Tip selection (10%, 15%, 20%)
- Animated tab/balance updates
- Mock payment flow (simulated payment links)

⚠️ **Requires Stripe MCP setup for real payments:**
- Real Stripe payment link generation
- Actual payment status checking

---

### Step 1: Create a Stripe Account (Test Mode)

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/register)
2. Create a free account (no credit card required for test mode)
3. Once logged in, ensure you're in **Test Mode** (toggle in top-right corner)
4. Navigate to **Developers → API Keys**
5. Copy your **Test mode** keys:
   - `Publishable key`: `pk_test_...`
   - `Secret key`: `sk_test_...`

> ⚠️ **Important**: Never use live keys! The implementation is designed for test mode only.

---

### Step 2: Install Stripe MCP Server

The Stripe MCP server provides the Model Context Protocol integration for payment operations.

```bash
# Option 1: Using uvx (recommended if you have uv installed)
# No installation needed - uvx runs it directly

# Option 2: Install uv if you don't have it
pip install uv
# or on macOS:
brew install uv
```

---

### Step 3: Configure Stripe MCP Server in Kiro

Create the MCP configuration file at `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "stripe": {
      "command": "uvx",
      "args": ["mcp-server-stripe"],
      "env": {
        "STRIPE_SECRET_KEY": "sk_test_YOUR_TEST_SECRET_KEY_HERE"
      },
      "disabled": false,
      "autoApprove": [
        "create_payment_link",
        "get_payment_link"
      ]
    }
  }
}
```

Replace `sk_test_YOUR_TEST_SECRET_KEY_HERE` with your actual Stripe test secret key.

---

### Step 4: Update Environment Variables (Optional)

Add to your `.env` file if you want to configure Stripe directly:

```bash
# Stripe Configuration (Test Mode Only!)
STRIPE_SECRET_KEY=sk_test_YOUR_TEST_SECRET_KEY_HERE
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_TEST_PUBLISHABLE_KEY_HERE
```

---

### Step 5: Verify Setup

1. Start MayaMCP: `mayamcp` or `python main.py`
2. Order a drink: "I'd like a martini"
3. Check your tab: "What's my tab?"
4. Add a tip: Click 15% tip button
5. Pay: "I'll pay my bill"

**Expected behavior:**
- With Stripe MCP configured: Real Stripe checkout link generated
- Without Stripe MCP: Mock payment link (still functional for demo)

---

### Testing Payment Flow

Use Stripe's test card numbers:
- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **Requires Auth**: `4000 0025 0000 3155`

Any future expiry date and any 3-digit CVC will work.

---

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Stripe MCP unavailable" | Check MCP server is running, verify API key |
| Mock payment links only | Stripe MCP not configured, check `.kiro/settings/mcp.json` |
| Payment link creation fails | Verify test mode key (starts with `sk_test_`) |
| Tab not updating | Check browser console for JavaScript errors |

---

### Architecture Notes

The implementation includes:
- **Graceful fallback**: If Stripe MCP is unavailable, mock payments work automatically
- **Idempotency**: Payment requests use `{session_id}_{timestamp}` keys to prevent duplicates
- **Retry logic**: 3 retries with exponential backoff (1s, 2s, 4s)
- **Test mode only**: The code enforces `test_mode=True` by default

---

## Other TODOs

- [ ] Add Grafana dashboard JSON for MayaMCP metrics
  - Create a dashboard JSON (store at `monitoring/grafana/maya-mcp-dashboard.json`).
  - Panels to include (Prometheus metrics exposed at `/metrics`):
    - `maya_config_memory_mb` (gauge)
    - `maya_config_max_containers` (gauge)
    - `maya_container_memory_usage_bytes` (gauge)
    - `maya_container_memory_limit_bytes` (gauge)
    - `maya_container_cpu_usage_seconds_total` (counter)
    - `maya_process_uptime_seconds` (gauge)
  - Prometheus datasource config: target `<modal-app-host>`, `metrics_path: /metrics`, `scheme: https`.
  - Add basic alerts (e.g., high memory usage %, low headroom, sustained CPU usage).
  - Document import steps in README and link to the JSON path.
  - Optional: version the dashboard file and include changelog notes.

- [ ] Implement actual Stripe MCP server calls in `src/payments/stripe_mcp.py`
  - Replace stub implementations in `_call_stripe_create_link()` and `_poll_payment_status()`
  - Integrate with kiroPowers tool for MCP communication
  - Add proper error handling for MCP server responses

- [ ] Add session lock cleanup background task
  - Implement scheduled cleanup for expired session locks (>1 hour inactive)
  - Register timer on app initialization
  - Add monitoring metrics for cleanup operations
