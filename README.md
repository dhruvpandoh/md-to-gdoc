# Markdown Meeting Notes, Google Doc (Google Docs API)

A Google Colab notebook + helper script that converts markdown meeting notes into a **well-formatted Google Doc** using the **Google Docs API**.

It supports:
- Heading mapping: H1 / H2 / H3
- Nested bullet lists (indentation preserved)
- Markdown checkboxes (`- [ ]`) - Google Docs checkboxes
- Assignee mentions like `@sarah` styled distinctly (bold + color)
- Footer section (after `---`) styled distinctly (italic + gray + smaller)

---

## Repo Structure

```
.
├── Markdown_to_Google_Doc.ipynb   # main Colab notebook
├── src/
│   └── md_to_gdoc.py              # (optional) extracted logic (same as notebook)
├── requirements.txt
└── README.md
```

---

## Dependencies

- `google-api-python-client`
- `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`
- `reportlab` (for generating the submission PDF with links)
- Python 3.10+ (Colab default)

Install in Colab:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib reportlab
```

---

## Setup (Google Colab)

1. Open `Markdown_to_Google_Doc.ipynb` in Google Colab.
2. Run the install cell.
3. Run the authentication cell:
   - You will be prompted to authorize access to your Google account.
4. Run the remaining cells to:
   - Parse markdown
   - Create a new Google Doc
   - Apply formatting
   - Print the Google Doc URL

> If you get a 403 error like *"Google Docs API has not been used..."*, enable the **Google Docs API** in your Google Cloud project and re-run.

---

## How to Run

In the notebook:
1. Edit `MARKDOWN_NOTES` (or read from a `.md` file).
2. Run the `create_formatted_doc(...)` cell.
3. Copy the printed Doc link.

Optional:
- Run the final cell to generate `submission_links.pdf` that contains your Doc / GitHub / Colab links.

---

## Notes / Design Choices

- Bullet nesting is inferred from leading spaces (2 spaces = 1 level).
- Mentions are detected using regex `@\w+` and styled via `updateTextStyle`.
- Google Docs checkbox bullets are created with `bulletPreset = BULLET_CHECKBOX`.

---

## License

MIT
