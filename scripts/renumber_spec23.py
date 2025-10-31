import re
from pathlib import Path

p = Path(r"e:/Dropbox/code/cidsem/docs/specs/spec23-Ontology.md")
s = p.read_text(encoding="utf-8")
# remove surrounding code fences if present
s = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", s)
s = re.sub(r"\n```\s*$", "", s)
lines = s.splitlines()

# find header start
header_idx = None
sep_idx = None
for i, ln in enumerate(lines):
    if re.match(r"^\|\s*ID\s*\|", ln):
        header_idx = i
        break
if header_idx is None:
    raise SystemExit("Table header not found")
# separator is next line typically
sep_idx = header_idx + 1
# collect data rows until a blank line or a line starting with ##
data_rows = []
for ln in lines[sep_idx + 1 :]:
    if ln.strip() == "":
        break
    if ln.strip().startswith("##"):
        break
    if not ln.strip().startswith("|"):
        break
    data_rows.append(ln)

# parse rows into (short, desc, category)
parsed = []
seen = set()
for ln in data_rows:
    parts = [p.strip() for p in ln.split("|")]
    # parts[0] is empty before first |, parts[1]=id, parts[2]=short, parts[3]=desc, parts[4]=category, parts[5] maybe empty
    if len(parts) < 5:
        continue
    short = parts[2]
    desc = parts[3]
    cat = parts[4]
    key = (short, desc, cat)
    if short in seen:
        continue
    seen.add(short)
    parsed.append(key)

# renumber sequentially starting at 1
out_lines = []
out_lines.append("# Ontology")
out_lines.append("")
out_lines.append(
    "| ID  | Short Name        | Description                                           | Category                |"
)
out_lines.append(
    "|-----|-------------------|-------------------------------------------------------|-------------------------|"
)
for idx, (short, desc, cat) in enumerate(parsed, start=1):
    id_str = f"{idx:03d}"
    out_lines.append(f"| {id_str} | {short} | {desc} | {cat} |")

# find label format enforcement section if present and append it
label_note = None
label_idx = None
for i, ln in enumerate(lines):
    if ln.strip().lower().startswith("## label format enforcement"):
        label_idx = i
        label_note = "\n".join(lines[i:])
        break
if label_note is None:
    # fallback default note
    label_note = '\n\n## Label format enforcement\n\nLabel format enforcement: ontology entries must use the fully-qualified form "kind:namespace:label" (exactly two colons between kind, namespace and the human label).\n'
else:
    label_note = "\n" + label_note

out = "\n".join(out_lines) + label_note
p.write_text(out, encoding="utf-8")
print(f"Rewrote {p} with {len(parsed)} entries")
