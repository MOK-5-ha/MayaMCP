# TODOs

## Stablecoin Payment Integration Setup (Base Sepolia Testnet)

The payment feature uses the Coinbase Developer Platform (CDP) AgentKit SDK for simulated stablecoin (USDC) payments on the Base Sepolia testnet. It works immediately in sandbox/simulation mode without any API keys.

### Current Status

✅ **Works immediately without any setup (simulation mode):**
- Tab overlay displays on Maya's avatar
- Balance tracking ($1000 starting balance)
- Tip selection (10%, 15%, 20%)
- Animated tab/balance updates
- Optimistic payment processing (instant tab clearing)
- Simulated blockchain transaction hash + BaseScan explorer link

⚠️ **Requires CDP setup for real testnet transactions:**
- Real USDC transfers on Base Sepolia
- Actual blockchain confirmation
- BaseScan-verifiable transaction hashes

---

### Step 1: Create a CDP Account

1. Go to [CDP Portal](https://portal.cdp.coinbase.com/)
2. Create a free account
3. Navigate to **API Keys**
4. Create a new API key pair (note the **API Key ID** and **API Key Secret**)

---

### Step 2: Configure Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# Coinbase Developer Platform (CDP) — Base Sepolia Testnet Payments
CDP_API_KEY_ID=your_key_id_here
CDP_API_KEY_SECRET=your_key_secret_here

# Optional: Private key for a persistent merchant wallet
CDP_MERCHANT_PRIVATE_KEY=

# Optional: Override receiver address for testnet payments
CDP_RECEIVER_ADDRESS=
```

---

### Step 3: Get Testnet Funds

1. Use the Base Sepolia faucet: [https://www.coinbase.com/faucets/base-sepolia](https://www.coinbase.com/faucets/base-sepolia)
2. Request test ETH for gas fees
3. Test USDC is requested automatically by the CDP SDK on first transaction

---

### Step 4: Verify Setup

1. Start MayaMCP: `mayamcp` or `./run_maya.sh`
2. Order a drink: "I'll have a martini"
3. Pay your bill: "I'll pay my bill"
4. Expected: Real tx hash returned, verifiable on [BaseScan Sepolia](https://sepolia.basescan.org/)

**Expected behavior:**
- With CDP keys configured: Real USDC transfer on Base Sepolia
- Without CDP keys: Simulated payment (still functional for demo, `is_simulated=True`)

---

### Testing Payment Flow

- **Normal payments**: Any amount processes successfully (optimistic clearing)
- **Force failure (testing)**: An amount of exactly **$99.99** triggers a simulated register malfunction
- **Simulation mode**: Works without CDP keys (`is_simulated=True` in response)

---

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Wallet service unavailable" | Check CDP API keys in `.env` |
| Simulated payments only | `CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` not configured |
| Transaction fails on-chain | Insufficient testnet ETH for gas; use faucet |
| Register malfunction message | Background tx failed — check logs for CDP errors |
| Tab not updating | Check browser console for JavaScript errors |

---

### Architecture Notes

The implementation includes:
- **Optimistic UI**: Tab clears instantly; blockchain confirmation happens in background
- **Graceful fallback**: Real CDP → simulated mode (no keys needed)
- **Thread-safe**: Background transactions use daemon threads with mutex-locked state updates
- **Failure handling**: Failed background txs update state; Maya reports register malfunction
- **Test mode**: Amount `$99.99` triggers deterministic failure for testing/evals

---

## Other TODOs

- [ ] Expand Weave evaluation dataset in `scripts/run_weave_evals.py`
  - Add more conversation flow test cases (e.g., testing memory retrieval and complex payment edge cases).

- [ ] Add session lock cleanup background task
  - Implement scheduled cleanup for expired session locks (>1 hour inactive)
  - Register timer on app initialization
  - Add monitoring metrics for cleanup operations
