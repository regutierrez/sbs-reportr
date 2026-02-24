import os
import re
import fitz


def extract_pdf_images(pdf_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)

    current_heading = "Unknown Heading"
    current_subheading = "Unknown Subheading"

    # Track counts to avoid overwriting files with the same heading/subheading
    image_counters = {}

    # Keep track of processed images by (page_num, xref, y_pos) to avoid exact duplicates
    processed_images = set()

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 1. Gather all text events
        events = []
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue

                        is_bold = "Bold" in span["font"]
                        size = span["size"]
                        y_pos = span["origin"][1]

                        # Heading heuristic: A. INTRODUCTION, B. DATA GATHERING...
                        if size > 13 and is_bold and re.match(r"^[A-Z]\.\s", text):
                            events.append({"type": "heading", "y": y_pos, "text": text})

                        # Subheading heuristic: B.1. Rebar Scanning, C.2. Rebar Scanning...
                        elif size > 10.5 and is_bold and re.match(r"^[A-Z]\.\d+\.\s", text):
                            events.append({"type": "subheading", "y": y_pos, "text": text})

        # 2. Gather all image events
        for img in page.get_image_info(xrefs=True):
            xref = img["xref"]
            y_pos = img["bbox"][1]  # Top Y coordinate of the image bounding box
            events.append({"type": "image", "y": y_pos, "xref": xref})

        # 3. Sort events by Y-coordinate (top to bottom)
        events.sort(key=lambda e: e["y"])

        # 4. Process events
        for event in events:
            if event["type"] == "heading":
                current_heading = re.sub(r'[\/:*?"<>|]', "-", event["text"])
                current_subheading = "Unknown Subheading"
            elif event["type"] == "subheading":
                current_subheading = re.sub(r'[\/:*?"<>|]', "-", event["text"])
            elif event["type"] == "image":
                xref = event["xref"]
                y_pos = event["y"]
                image_key = (page_num, xref, int(y_pos))

                if image_key in processed_images:
                    continue

                try:
                    img_dict = doc.extract_image(xref)
                except Exception as e:
                    print(f"Failed to extract image xref {xref}: {e}")
                    continue

                # Filter out small UI elements, logos, frames (usually PNGs or very small files)
                ext = img_dict["ext"]
                img_data = img_dict["image"]

                # Heuristic: Real photos in this PDF report are JPEGs and > 10KB
                if ext != "jpeg" or len(img_data) < 10000:
                    continue

                processed_images.add(image_key)

                # Create base filename
                if current_subheading == "Unknown Subheading":
                    base_name = f"{current_heading}"
                else:
                    base_name = f"{current_heading} - {current_subheading}"

                # Increment counter for this specific base name
                if base_name not in image_counters:
                    image_counters[base_name] = 1
                else:
                    image_counters[base_name] += 1

                count = image_counters[base_name]
                filename = f"{base_name} - {count}.{ext}"
                filepath = os.path.join(output_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(img_data)
                print(f"Saved: {filename}")


if __name__ == "__main__":
    pdf_path = "docs/Testing Report Template_v0.pdf"
    output_dir = "extracted_images"
    print(f"Extracting images from {pdf_path} into {output_dir}...")
    extract_pdf_images(pdf_path, output_dir)
    print("Extraction complete.")
