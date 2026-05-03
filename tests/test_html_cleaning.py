from bs4 import BeautifulSoup

from changescout.html_cleaning import extract_title


def test_extract_title_ignores_javascript_notice_and_uses_html_title():
    html = """
    <html>
      <head>
        <title>VERAS - Verkehrsinfrastruktur-Entwicklung Raum Suhr - Kanton Aargau</title>
      </head>
      <body>
        <main>
          <h1>JavaScript deaktiviert oder nicht unterstützt.</h1>
          <article>
            <h2>Projekt</h2>
            <p>Content</p>
          </article>
        </main>
      </body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")

    assert extract_title(soup) == "VERAS - Verkehrsinfrastruktur-Entwicklung Raum Suhr"