# Deploy the contract on Studio Next (no coding needed)

1. Open GenLayer Studio and switch the network to **Studio Next** (RPC https://studio-next.genlayer.com/api, chain ID 61997).
2. Create a new contract file named `repo_trust.py` and paste the full contents of `contracts/repo_trust.py`. Keep the first two comment lines exactly as they are.
3. In the deploy panel, set the constructor value `review_fee` to `0` (reviews are free). To charge a fee later, use a number in wei, for example `10000000000000000` for 0.01 GEN.
4. Click **Deploy** and wait until the transaction shows as accepted.
5. Copy the contract address (it starts with `0x`). Also confirm it on https://explorer-studio-dev.genlayer.com/.
6. Run `get_version` in Studio. It should return `1.0.0`.
7. Test in Studio before building the site: run `review` with `vercel/next.js`, then `get_review` with the same text. You should see a verdict. Try `review` with `not a repo`; it should succeed and `get_last_result` should say `ERR:INVALID_REPO`.
8. Paste the address into `deployments/studio-next.json`.
