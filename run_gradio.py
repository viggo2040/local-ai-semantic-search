"""
Launcher principal Gradio.

Fase 13.1:
- importa demo sin lanzar automaticamente desde gradio_ui.app;
- inicia UI local en 127.0.0.1:7860 por defecto;
- permite puerto alternativo mediante GRADIO_SERVER_PORT.
"""

import os

from gradio_ui.app import demo


if __name__ == "__main__":
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7861"))

    demo.launch(
        server_name="127.0.0.1",
        server_port=server_port,
    )
