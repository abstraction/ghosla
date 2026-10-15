---
name: abstraction-signature
description: >-
  Use this skill when the user asks to generate, update, or add their repo signature, logo, or header.
  It generates a pixel-perfect SVG of a geometric logo (like "abstraction" or "subgen") in 3 different variants: default, compact, and legible.
---

# Abstraction Repo Signature

Generate SVG pixel-art logos for GitHub repository READMEs. This is a uniform branding element used across all of the user's repositories.

## Execution rules

- **Treat `generate.js` as an opaque CLI.** Do NOT read its source, run `--help`, or invoke its dependencies (figlet, etc.) directly. The interface is fully documented below.
- **Do NOT inspect other repos** for reference on how to embed the logo. The embed pattern is below.
- **Do NOT generate test or throwaway SVGs.** Generate directly to the final output prefix (`logo`).
- **Do NOT read the generated SVG source** to verify it. The script is deterministic; if it exits 0, the output is correct.
- **Infer the text** from the repository directory name (e.g., `youtube.txt`, `subgen`) unless the user specifies something different.
- **Default variant is `default`** unless the user asks for a specific one.

## Variants

| Variant   | Style                                         | When to use                           |
| --------- | --------------------------------------------- | ------------------------------------- |
| `default` | Wide 10×10 pixel squares (miniwi font)        | Default choice                        |
| `compact` | Narrow 6×12 terminal proportions (miniwi font) | User wants denser/narrower            |
| `legible` | Readable letters (Small Block font)           | User wants legibility over aesthetics |

## Steps

### 1. Read `README.md`

Read enough of the file to understand its top-level structure and decide where the logo goes:

- **Existing header** (a `<pre>` ASCII block, an old `<img>` tag, a `<div align="center">` banner, or any banner-like element near the top): replace the entire header block with the embed below.
- **`# H1` heading at the top**: if the README starts with a markdown `# Title` that matches or restates the repo name, **remove it** — the logo replaces it.
- **Tagline / subtitle**: look for a one-line description, subtitle, or summary immediately following the old header or title. Extract it to include inside the centered `<div align="center">` header block rather than leaving it below the horizontal rule.
- **No header yet** (new repo, or README starts with body content): insert the embed at the very top, before everything else.

Use your judgment. The logo and optional tagline form a centered branded header that replaces the need for a text `# Title`.

### 2. Generate the SVGs

```bash
~/.gemini/config/skills/abstraction-signature/scripts/generate.js \
  --text "<repo-name>" --variant default --out logo
```

Replace `<repo-name>` with the inferred or user-specified text. The `--out` argument is a prefix relative to cwd; run from the repo root so `logo-light.svg` and `logo-dark.svg` land there.

### 3. Update `README.md`

Insert or replace so the top of the file contains this exact structure — a centered div containing the logos using GitHub's `<picture>` syntax (and optional tagline) followed by a horizontal rule to separate the header from the body:

```html
<div align="center">
  <p>
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="./logo-light.svg">
      <img alt="<repo-name>" src="./logo-light.svg" height="80">
    </picture>
  </p>
  <tagline-with-html-tags>
</div>

---
```

If the repository does not have a subtitle or tagline, omit the tagline line:

```html
<div align="center">
  <p>
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="./logo-light.svg">
      <img alt="<repo-name>" src="./logo-light.svg" height="80">
    </picture>
  </p>
</div>

---
```

**Crucial formatting rule for the tagline:**
Because CommonMark / GitHub Flavored Markdown (GFM) treats `<div align="center">` and `<p>` as raw HTML blocks, **Markdown syntax is not parsed inside them**. Always convert any inline Markdown syntax within the tagline into semantic HTML:
- Backticks `` `code` `` $\rightarrow$ `<code>code</code>`
- Links `[text](url)` $\rightarrow$ `<a href="url">text</a>`
- Bold `**text**` $\rightarrow$ `<strong>text</strong>`
- Italics `*text*` $\rightarrow$ `<em>text</em>`

Preserve everything else in the README below the `---` separator.
