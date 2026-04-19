# Steganography Site

A full-stack assignment project for hiding a secret message or secret file inside another file using bit-level steganography, then publishing the modified carrier on a public site.

## Features
- User registration and login
- Public gallery of stego posts
- Authenticated upload/publish flow
- Embed **secret text** or a **secret file** into any carrier file
- Reversible extraction flow using the same **S**, **L**, and **C** values
- Image preview for public image posts

## Assignment mapping
- **P** = carrier file uploaded by the user
- **M** = secret text or secret file
- **S** = starting bit offset
- **L** = periodic interval for replacement
- **C** = mode controlling how `L` changes over time

Supported modes in this project:
- `fixed` → constant `L`
- `cycle` → cycles through `L`, `2L`, and `3L+4`
- `increment` → `L`, `L+1`, `L+2`, ...

## How the embedding works
1. Read the carrier file as bytes.
2. Read the secret text/file as bytes.
3. Build a payload header containing:
   - magic bytes (`STEG`)
   - secret length
   - secret filename length
   - secret filename
4. Convert both carrier and payload into bit arrays.
5. Starting at bit `S`, replace every `L`-controlled bit with payload bits.
6. Save the modified carrier and publish it.

## How extraction works
1. Read the stego file.
2. Use the same `S`, `L`, and `C` values.
3. Reconstruct the embedded header first.
4. Determine the hidden file length from the header.
5. Extract the full payload and restore the original secret.

## How someone could find M or P given only L
Knowing only `L` is usually **not enough** to recover the hidden message. An attacker would still need:
- the correct start bit `S`
- the correct mode `C`
- a way to know where the payload begins and ends
- some method to distinguish real payload bits from normal file noise

With only `L`, the attacker would likely need to try many possible values of `S`, different modes, and many possible payload lengths. That makes recovery much harder, though not impossible if the attacker already knows the file format or has the original carrier.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:
- `http://127.0.0.1:8000`

## Demo flow
1. Register a user.
2. Log in.
3. Go to **Upload**.
4. Upload a carrier file.
5. Enter secret text or choose a secret file.
6. Pick `S`, `L`, and `mode`.
7. Publish the stego file.
8. View the public post.
9. Go to **Extract** and use the same parameters to recover the secret.

## Notes
- For images, choose a larger carrier file if your message is large.
- If the carrier is too small, the app will show an error.
- In production, move the session secret into an environment variable.
