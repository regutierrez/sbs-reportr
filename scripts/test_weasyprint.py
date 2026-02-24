from weasyprint import HTML

html = """
<!doctype html>
<html>
<body>
  <div style="display: grid; grid-template-columns: 1fr 1fr;">
    <div style="display: contents;">
        <img src="test.jpg" />
    </div>
  </div>
</body>
</html>
"""

try:
    HTML(string=html).write_pdf("test.pdf")
    print("Success")
except Exception as e:
    import traceback

    traceback.print_exc()
