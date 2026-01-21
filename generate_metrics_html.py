import requests

def fetch_metrics(url):
    response = requests.get(url)
    return response.text

def generate_html(metrics):
    html = """
    <html>
    <head>
        <title>Node Exporter Metrics</title>
        <style>
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h2>Node Exporter Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
    """
    for line in metrics.split('\n'):
        if line and not line.startswith('#'):
            parts = line.split(' ')
            metric = parts[0]
            value = parts[1] if len(parts) > 1 else ''
            html += f"<tr><td>{metric}</td><td>{value}</td></tr>"

    html += """
        </table>
    </body>
    </html>
    """
    return html

def save_html(content, filename='metrics.html'):
    with open(filename, 'w') as file:
        file.write(content)

if __name__ == "__main__":
    url = "http://localhost:9100/metrics"
    metrics = fetch_metrics(url)
    html_content = generate_html(metrics)
    save_html(html_content)
    print("Metrics saved to metrics.html")
