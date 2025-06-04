Burp API DocLogger

A Burp Suite extension that automatically logs API endpoints and exports them into interactive Swagger/OpenAPI HTML documentation.

Features

- Logs API calls
- Captures query parameters, request body, and Authorization header
- Exports to standalone `api-docs.html` with:
  - Editable base URL
  - Editable Authorization token
  - Executable Swagger UI

Installation

1. Open **Burp Suite**
2. Go to **Extender → Extensions**
3. Click **Add** and load `api_Doclogger.py` with:
   - **Extension Type**: Python
   - **Environment**: Jython (e.g., `jython-standalone-2.7.x.jar`)

4. Once loaded, a new tab **"API DocLogger"** will appear
5. Click **Export OpenAPI HTML** after capturing requests

Requirements

- Burp Suite (Community or Pro)
- Jython (2.7.x)


Demo
![Demo](https://github.com/user-attachments/assets/8ccb9eca-ae4e-40f5-9546-cac39e9ce532)

