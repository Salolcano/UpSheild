# Step by step (no coding needed)

## A. Deploy the contract
1. Open GenLayer Studio and switch to Studio Next (RPC https://studio-next.genlayer.com/api, chain ID 61997).
2. Create a new file named `upshield.py` and paste everything from `contracts/upshield.py`.
3. Click Deploy (no inputs needed). Copy the contract address.
4. Send the address back to Claude so the site can be connected.

## B. Put the app online with Vercel
1. Create a free account at github.com and make a new repository called UpShield.
2. Click "uploading an existing file", drag in everything from this folder, and commit.
3. Create a free account at vercel.com, click "Add New... Project", pick the UpShield repository.
4. Before deploying, open "Environment Variables" and add VITE_UPSHIELD_CONTRACT = your contract address (and optionally VITE_GENLAYER_RPC = https://studio-next.genlayer.com/api). Then click Deploy. Vercel gives you a link.
5. Paste that link into the submission form.

## C. Test it
0. Run `npm test` first (needs Node and Python). All tests should pass.
1. Fund the pool, request a quote for a window starting 40+ minutes from now, buy cover within 60 minutes, then check the claim after the window closes.
2. Copy the real transaction hashes into README.md.

## D. Your wallet needs GEN for fees
Studio Next charges a fee on every transaction. Before using the website, make sure the wallet you connect holds GEN on Studio Next (chain ID 61997). Fund the pool with an amount that leaves some GEN for fees. If a transaction fails with a fee error, send me the message.
