# -*- coding: utf-8 -*-
from burp import IBurpExtender, IHttpListener, ITab
from javax.swing import JPanel, JButton, JFileChooser
from java.awt import BorderLayout
import threading, os, json

class BurpExtender(IBurpExtender, IHttpListener, ITab):
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        callbacks.setExtensionName("API DocLogger")
        callbacks.registerHttpListener(self)

        self.logged_endpoints = {}
        self.lock = threading.Lock()

        self._panel = JPanel(BorderLayout())
        self._export_button = JButton("Export OpenAPI HTML", actionPerformed=self.exportDocs)
        self._panel.add(self._export_button, BorderLayout.NORTH)
        callbacks.addSuiteTab(self)

    def getTabCaption(self):
        return "API DocLogger"

    def getUiComponent(self):
        return self._panel

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        if not messageIsRequest:
            analyzedRequest = self._helpers.analyzeRequest(messageInfo)
            headers = analyzedRequest.getHeaders()
            method = analyzedRequest.getMethod()
            url = analyzedRequest.getUrl()
            path = url.getPath()

            if not any(p in path for p in ["/api", "/v1", "/v2", "/v3", "/rest"]):
                return
            if any(path.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".svg", ".ico", ".woff", ".ttf"]):
                return

            content_type = None
            for h in headers:
                if h.lower().startswith("content-type:"):
                    content_type = h.lower()
                    break
            if content_type and "application/json" not in content_type:
                return

            query = url.getQuery()
            request = messageInfo.getRequest()
            body_offset = analyzedRequest.getBodyOffset()
            body = request[body_offset:].tostring()

            with self.lock:
                if path not in self.logged_endpoints:
                    self.logged_endpoints[path] = {}

                if method not in self.logged_endpoints[path]:
                    self.logged_endpoints[path][method] = {
                        "query": set(),
                        "body": body,
                        "responses": set(),
                        "auth": None
                    }

                for header in headers:
                    if header.lower().startswith("authorization:"):
                        self.logged_endpoints[path][method]["auth"] = header.split(":", 1)[1].strip()

                if query:
                    for param in query.split("&"):
                        key = param.split("=")[0]
                        self.logged_endpoints[path][method]["query"].add(key)

                response = messageInfo.getResponse()
                if response:
                    status_code = self._helpers.analyzeResponse(response).getStatusCode()
                    self.logged_endpoints[path][method]["responses"].add(status_code)

    def exportDocs(self, event):
        chooser = JFileChooser()
        chooser.setDialogTitle("Select output directory")
        chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
        if chooser.showSaveDialog(self._panel) == JFileChooser.APPROVE_OPTION:
            out_dir = chooser.getSelectedFile().getAbsolutePath()
            self._generateHtml(os.path.join(out_dir, "api-docs.html"))
            print("[+] Exported HTML to:", os.path.join(out_dir, "api-docs.html"))

    def _generateHtml(self, path):
        api_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "API Documentation",
                "version": "1.0.0"
            },
            "paths": {}
        }

        base_url = "http://localhost:8888"
        auth_header = ""

        for path_key, methods in self.logged_endpoints.items():
            api_spec["paths"][path_key] = {}
            for method, meta in methods.items():
                op = {
                    "summary": "%s %s" % (method, path_key),
                    "responses": {
                        str(code): {"description": "Response %d" % code}
                        for code in meta["responses"]
                    },
                    "parameters": [],
                    "servers": []
                }

                for q in sorted(meta["query"]):
                    op["parameters"].append({
                        "name": q,
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"}
                    })

                if meta["body"] and method.upper() == "POST":
                    op["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                                "example": meta["body"]
                            }
                        }
                    }

                if meta["auth"]:
                    auth_header = meta["auth"]

                op["servers"].append({ "url": base_url })
                api_spec["paths"][path_key][method.lower()] = op

        spec_json = json.dumps(api_spec)

        html_template = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>API Documentation</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
</head>
<body>
  <div style="margin: 10px">
    <label>Base URL: </label>
    <input id="baseUrl" type="text" value="%s" style="width:300px;" />
    <button onclick="applyBaseUrl()">Apply</button><br><br>
    <label>Authorization Header: </label>
    <input id="authHeader" type="text" value="Bearer %s" style="width:600px;" />
    <button onclick="applyAuth()">Apply</button>
  </div>
  <div id="swagger-ui"></div>
  <footer style="text-align:center;margin-top:40px;">
    <a href='https://github.com/EngAnasAlzahrani' target='_blank' style="text-decoration: none;">
      <img src='https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png' style='width:24px;height:24px;margin-right:6px;vertical-align:middle;'/>
    </a>
  </footer>
  <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
  <script>
    var spec = %s;
    var ui;

    function applyBaseUrl() {
      var baseUrl = document.getElementById('baseUrl').value;
      for (const path in spec.paths) {
        for (const method in spec.paths[path]) {
          spec.paths[path][method].servers = [{ url: baseUrl }];
        }
      }
      renderUI();
    }

    function applyAuth() {
      var authHeader = document.getElementById('authHeader').value;
      ui = SwaggerUIBundle({
        spec: spec,
        dom_id: '#swagger-ui',
        requestInterceptor: function(req) {
          req.headers['Authorization'] = authHeader;
          return req;
        },
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ]
      });
    }

    function renderUI() {
      applyAuth();
    }

    renderUI();
  </script>
</body>
</html>
""" % (base_url, auth_header, spec_json)

        with open(path, "w") as f:
            f.write(html_template)
