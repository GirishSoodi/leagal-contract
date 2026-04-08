import os

for root, _, files in os.walk("."):
    for f in files:
        path = os.path.join(root, f)

        # Skip unwanted folders
        if any(x in path for x in [".venv", "__pycache__"]):
            continue

        try:
            with open(path, "rb") as file:
                data = file.read()
                data.decode("utf-8")
        except Exception as e:
            print("❌ BAD FILE:", path)
            print("   Error:", e)
            exit()  # stop at first bad file

print("✅ All files are UTF-8 clean")