import json

with open("build/line_map.json", "r") as fp:
    line_map = json.load(fp)

# The lines we care about from the error log:
lines_of_interest = [668, 681, 984, 1048, 1062, 1104, 1181, 1182, 1183, 1185, 1186, 1187, 1189, 1190, 1191, 1193, 1194, 1214, 1225]

for l in lines_of_interest:
    print(f"Flattened Line {l} -> {line_map.get(str(l))}")

