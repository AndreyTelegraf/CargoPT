# CargoPT Hero Visual Source of Truth

This package contains the approved Hero card references extracted from the target screenshot.

Important:

- The `.png` files are pixel-accurate crops from the approved design reference.
- The `.svg` files are reference wrappers embedding those exact crops.
- These SVGs are not final production vectors yet.
- They are the correct next step: stable visual references that can be used to manually reconstruct clean SVG vectors without guessing.

Recommended workflow:

1. Put this folder under `docs/design/hero/source/`.
2. Use `cards/*.svg` as the locked visual reference layer.
3. Rebuild each production SVG manually on top of the reference, one card at a time.
4. Compare the final SVG to the reference crop before implementation.
5. Only after all four card SVGs are accepted, integrate them into the landing Hero.

This avoids the previous failure mode: trying to describe or recreate the card illustrations from memory.
