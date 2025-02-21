with open('newSorted.csv', 'r') as file:
    content = file.read()
content = content.strip().strip('"')
lines = content.splitlines()

clean_lines = []
for line in lines:
    line = line.strip()
    if line.startswith("```"):
        continue
    if line.startswith("track_id"):
        continue
    clean_lines.append(line)

#writing cleaned csv
with open('cleaned.csv', 'w', newline='') as outfile:
    outfile.write("track_id, language" + "\n")

with open('cleaned.csv', 'a', newline='') as outfile:
    for line in clean_lines:
        outfile.write(line + "\n")