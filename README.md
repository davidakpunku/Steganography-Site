# Steganography Site

# Name: David Akpunku
# Student ID: 1002126466
# Azure Live Site: https://steganography-site-david-gceveae9f0dthkem.centralus-01.azurewebsites.net

---

### How to Use the Website

### 1. Public Gallery (No login required)
   - Visit the homepage to see all publicly posted steganography images.
   - Click on any post to view the image and its parameters (S, L, Mode).

### 2. Register / Login (Required for uploading)
   - Click Register to create a new account.
   - Or click Login if you already have an account.

### 3. Upload & Hide a Message
   - After logging in, go to Upload.
   - Choose a carrier image (PNG recommended).
   - Enter a secret text message or upload a secret file.
   - Set the parameters:
     - S = Starting bit offset (e.g., 100–500)
     - L = Interval / periodicity (e.g., 4 or 8)
     - Mode = `fixed`, `cycle`, or `increment`
   - Click Embed and Publish.
   - The stego image will be posted publicly.

### 4. Extract Hidden Message
   - Login → go to Extract.
   - Upload any posted stego image.
   - Enter the exact same S, L, and Mode used during embedding.
   - Click Extract to recover the original secret message/file.

---

### Discussion Question: How someone could find M or P, given (only) L

Knowing only the periodicity `L` is not sufficient to reliably recover the hidden message M or the original carrier P.

An attacker would still need:
- The correct starting bit offset S
- The correct mode C (`fixed`, `cycle`, or `increment`)
- Knowledge of the payload header format (our magic bytes `STEGO1` + length fields)
- A way to distinguish the embedded bits from natural image noise

Because only selected bits are modified, the changes are similar to normal image compression noise. Without knowing S and C, the attacker would have to brute-force many possible combinations of starting positions, modes, and payload lengths. This makes recovery extremely difficult and computationally expensive.

---

### Features Implemented
- User registration and login (authenticated uploads only)
- Public gallery for viewing all posted stego images
- Support for hiding text or any file inside an image carrier
- Three modes: `fixed`, `cycle`, `increment`
- Fully reversible extraction using the same S, L, C parameters
- Deployed on Microsoft Azure (free tier)

### Project successfully fulfills all requirements of the assignment.
